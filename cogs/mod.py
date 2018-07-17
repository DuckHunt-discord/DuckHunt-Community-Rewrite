import discord
from discord.ext import commands
from cogs.helpers.checks import have_required_level


# Some of the code and converters are stolen from robo.danny source code
# https://raw.githubusercontent.com/Rapptz/RoboDanny/rewrite/cogs/mod.py

from cogs.helpers.mod_actions import Kick, Ban, Unban, Softban, Warn


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
