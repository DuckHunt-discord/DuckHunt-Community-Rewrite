import datetime
import json
import time

import discord


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