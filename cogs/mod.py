import datetime
import json
import time

import discord
from discord.ext import commands
from cogs.helpers.checks import have_required_level


# Some of the code and converters are stolen from robo.danny source code
# https://raw.githubusercontent.com/Rapptz/RoboDanny/rewrite/cogs/mod.py


class MemberID(commands.Converter):
    # Using IDs everywhere in place of member will allow us to ban/warn/... people who left already.
    # Doing so, every command should work just fine :)
    # Even if people left, is mods use IDs to invoke them.

    async def convert(self, ctx, argument):
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                return int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f"{argument} is not a valid member or member ID.") from None
        else:
            # Since this is a converter to ID, and we successfully got a Member object
            # We will check that the user is able to perform moderation actions on specified users
            # So that mods can't ban other mods, or the owner

            can_execute = ctx.author.id in ctx.bot.admins or ctx.author == ctx.guild.owner or ctx.author.top_role > m.top_role

            if not can_execute:
                raise commands.BadArgument('You cannot do this action on this user due to role hierarchy.')

            return m.id


class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        ban_list = await ctx.guild.bans()
        try:
            member_id = int(argument, base=10)
            entity = discord.utils.find(lambda u: u.user.id == member_id, ban_list)
        except ValueError:
            entity = discord.utils.find(lambda u: str(u.user) == argument or "@" + str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument("Not a valid previously-banned member.")
        return entity


class BaseAction:
    def __init__(self, ctx, on, reason):
        self.logging_channel = ctx.guild.get_channel(317432206920515597)
        self.logging_embed_colour = discord.Colour.light_grey()
        self.action = "Base Action"
        self.logging_embed_title = "{action} | Case #{case_number}"

        self.ctx = ctx
        self.on = on
        self.reason = reason

        self.root_dir = "mods/"

        with open(self.root_dir + "/current_case.txt", "r") as file:
            self.current_case = int(file.read())
        with open(self.root_dir + "/current_case.txt", "w") as file:
            file.write(str(self.current_case + 1))

    @property
    def formatted_reason(self):
        if self.reason is None:
            reason = f"Action done by {self.ctx.author} (ID: {self.ctx.author.id})\n" \
                     f"No reason was provided by the moderator"
        else:
            reason = f"Action done by {self.ctx.author} (ID: {self.ctx.author.id})\n\n" \
                     f"Reason given by the moderator:\n" \
                     f"{self.reason}"

        return reason

    async def _get_embed(self):
        e = discord.Embed()
        e.colour = self.logging_embed_colour
        e.title = self.logging_embed_title.format(case_number=self.current_case, action=self.action)
        e.description = self.reason
        e.add_field(name="Responsible Moderator", value=str(self.ctx.author) + " (" + self.ctx.author.mention + ")", inline=False)
        e.add_field(name="Victim", value=(str(self.on) if not isinstance(self.on, discord.Object) else "") + " (<@" + str(self.on.id) + ">)", inline=False)
        e.timestamp = datetime.datetime.now()
        e.set_author(name=self.on.id)
        return e

    async def log(self):
        self.ctx.logger.warning(f"[MOD] {self.action}-ing user {self.on} - by {self.ctx.author}")

        await self.logging_channel.send(embed=await self._get_embed())

    async def log_to_file(self):
        # USER LOG

        try:
            with open(self.root_dir + "/users/" + str(self.on.id) + ".json", "r") as infile:
                user_log = json.load(infile)
        except FileNotFoundError:
            user_log = []

        user_log.append(self.current_case)

        with open(self.root_dir + "/users/" + str(self.on.id) + ".json", "w") as outfile:
            json.dump(user_log, outfile)

        # CASE LOG

        action_logged = {"date": int(time.time()),
                         "action": self.action,
                         "reason": self.reason,
                         "moderator_id": self.ctx.author.id,
                         "moderator_screenname": self.ctx.author.name + "#" + self.ctx.author.discriminator,
                         "victim_id": self.on.id,
        }

        with open(self.root_dir + "/cases/" + str(self.current_case) + ".json", "w") as outfile:
            json.dump(action_logged, outfile)

    async def execute(self):
        pass

    async def do(self):
        try:
            await self.on.send(embed=await self._get_embed())
        except:
            self.ctx.logger.exception("Couldn't send action-message to user. It may be normal, as if the user is no longer in the server.")

        try:
            await self.log()
        except:
            self.ctx.logger.exception("Error logging mod action")
            await self.ctx.send_to(":x: Error logging your action, please report the bug to Eyesofcreeper. I'll try to execute it to the end. Please check.")

        await self.execute()
        await self.ctx.send_to(":ok_hand:", delete_after=60)


class Kick(BaseAction):

    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.red()
        self.action = "Kick"

    async def execute(self):
        await self.on.kick(reason=self.reason)


class Ban(BaseAction):
    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.dark_red()
        self.action = "Ban"

        if isinstance(on, int):
            self.on = discord.Object(id=self.on)

    async def execute(self):
        await self.ctx.guild.ban(self.on, reason=self.formatted_reason)


class Unban(BaseAction):
    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.green()
        self.action = "UnBan"

        if isinstance(on, int):
            self.on = discord.Object(id=self.on)
        elif isinstance(on, discord.guild.BanEntry):
            self.on = on.user
            self.ban_reason = on.reason

    async def execute(self):
        await self.ctx.guild.unban(self.on, reason=self.formatted_reason)
        if self.ban_reason:
            await self.ctx.send_to(f":information_desk_person: UnBan recorded. Previous ban reason : \n{self.ban_reason}.")


class Softban(BaseAction):
    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.dark_orange()
        self.action = "SoftBan"

        if isinstance(on, int):
            self.on = discord.Object(id=self.on)

    async def execute(self):
        await self.ctx.guild.ban(self.on, reason=self.formatted_reason)
        await self.ctx.guild.unban(self.on, reason=self.formatted_reason)


class Warn(BaseAction):
    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.orange()
        self.action = "Warn"

        if isinstance(on, int):
            self.on = discord.Object(id=self.on)


class Mod:
    """
    Moderation commands for the bot.

    Here you'll find, commands to ban, kick, warn and add notes to members.

    As a technical remainder, moderator is role 3 in the checks.get_level hierarchy.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @have_required_level(3)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """
        Kicks a member from the server.
        In order for this to work, the bot must have Kick Member permissions.
        """

        a = Kick(ctx, member, reason)
        await a.do()

    @commands.command()
    @commands.guild_only()
    @have_required_level(3)
    async def ban(self, ctx, member: MemberID, *, reason: str = None):
        """
        Bans a member from the server.
        You can also ban from ID to ban regardless whether they're
        in the server or not.
        In order for this to work, the bot must have Ban Member permissions.
        """

        a = Ban(ctx, member, reason)
        await a.do()

    @commands.command()
    @commands.guild_only()
    @have_required_level(3)
    async def softban(self, ctx, member: MemberID, *, reason: str = None):
        """
        Soft bans a member from the server.
        A softban is basically banning the member from the server but
        then unbanning the member as well. This allows you to essentially
        kick the member while removing their messages.
        In order for this to work, the bot must have Ban Member permissions.
        """
        a = Softban(ctx, member, reason)
        await a.do()

    @commands.command()
    @commands.guild_only()
    @have_required_level(3)
    async def unban(self, ctx, member: BannedMember, *, reason: str = None):
        """
        Unbans a member from the server.
        You can pass either the ID of the banned member or the Name#Discrim
        combination of the member. Typically the ID is easiest to use.
        In order for this to work, the bot must have Ban Member permissions.
        """

        a = Unban(ctx, member, reason)
        await a.do()

    @commands.command()
    @commands.guild_only()
    @have_required_level(3)
    async def warn(self, ctx, member: MemberID, *, reason: str = None):
        """
        Warns a member
        """

        a = Warn(ctx, member, reason)
        await a.do()


def setup(bot):
    bot.add_cog(Mod(bot))
