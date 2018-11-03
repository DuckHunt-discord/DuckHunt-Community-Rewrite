import datetime
import json
import time
from collections import Counter

import discord


def get_case_list(user:discord.User):
    try:
        with open(f'mods/users/{user.id}.json', 'r') as f:
            casenumbers_list = json.load(f)
    except FileNotFoundError:
        return []

    case_list = []
    for case_number in casenumbers_list:
        with open(f'mods/cases/{case_number}.json', 'r') as f:
            case_json = json.load(f)

        action = case_json['action']
        if action == 'Kick':
            case = Kick.get_old(case_json)
        elif action == 'Ban':
            case = Ban.get_old(case_json)
        elif action == 'Unban':
            case = Unban.get_old(case_json)
        elif action == 'SoftBan':
            case = Softban.get_old(case_json)
        elif action == 'Warn':
            case = Warn.get_old(case_json)
        elif action == 'Note':
            case = Note.get_old(case_json)
        else:
            raise IndexError(f'Unknown action type in json file mods/cases/{case_number}.json')

        case_list.append(case)

    return case_list


class BaseAction:

    @classmethod
    def get_old(cls, case_json):
        instance = cls(None, case_json['victim_id'], case_json['reason'])
        instance.moderator_str = case_json['moderator_screenname']

        return instance

    def __init__(self, ctx, on, reason):
        self.on = on
        if ctx:
            if isinstance(on, int):
                m = ctx.guild.get_member(on)
                if m:
                    self.on = m
                else:
                    self.on = discord.Object(id=self.on)
            self.logging_channel = ctx.guild.get_channel(317432206920515597)
            on_id = on.id if not isinstance(on, int) else on
            self.moderator_str = (str(ctx.author) + " (" + ctx.author.mention + ")") if ctx.author.id != on_id else f"AutoMod by {ctx.bot.user.mention}"

        self.logging_embed_colour = discord.Colour.light_grey()
        self.action = "Base Action"
        self.logging_embed_title = "{action} | Case #{case_number}"

        self.ctx = ctx
        self.reason = reason

        self.root_dir = "mods/"

        with open(self.root_dir + "/current_case.txt", "r") as file:
            self.current_case = int(file.read())
        with open(self.root_dir + "/current_case.txt", "w") as file:
            file.write(str(self.current_case + 1))
        if ctx:
            ctx.logger.debug(f"Created mod action with params {self.action}(ctx={self.ctx}, on={self.on}, reason={self.reason})")

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
        e.add_field(name="Responsible Moderator", value=self.moderator_str, inline=False)
        e.add_field(name="Victim", value=(str(self.on) if not isinstance(self.on, discord.Object) else "") + " (<@" + str(self.on.id) + ">)", inline=False)
        e.timestamp = datetime.datetime.now()
        e.set_author(name=self.on.id)
        return e

    async def log(self):
        self.ctx.logger.warning(f"[MOD] {self.action}-ing user {self.on} - by {self.ctx.author}")
        await self.log_to_file()

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

    async def thresholds_enforcer(self):

        if isinstance(self, Note) or isinstance(self, Unban):
            return

        next_treshold = {Warn: Kick,
                         Kick: Softban,
                         Softban: Ban,
                         Ban: Ban}

        # noinspection PyTypeChecker
        previous_cases = get_case_list(self.on)
        previous_case_types = Counter([type(c) for c in previous_cases])

        previous_this = previous_case_types[type(self)]
        if previous_this > 0 and previous_this % 5 == 0:
            # noinspection PyTypeChecker
            treshold = next_treshold[type(self)](self.ctx, self.on, f'Treshold enforcing : {self.action}*{previous_this} % 5 == 0')
            await treshold.do(tresholds=False)

    async def do(self, tresholds=True):
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
        if tresholds:
            await self.thresholds_enforcer()


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

    async def execute(self):
        await self.ctx.guild.ban(self.on, reason=self.formatted_reason)


class Unban(BaseAction):
    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.green()
        self.action = "UnBan"

        if isinstance(on, discord.guild.BanEntry):
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

    async def execute(self):
        await self.ctx.guild.ban(self.on, reason=self.formatted_reason)
        await self.ctx.guild.unban(self.on, reason=self.formatted_reason)


class Warn(BaseAction):
    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.orange()
        self.action = "Warn"


class Note(BaseAction):
    def __init__(self, ctx, on, reason):
        super().__init__(ctx, on, reason)

        self.logging_embed_colour = discord.Colour.dark_grey()
        self.action = "Note"

        if isinstance(on, int):
            self.on = discord.Object(id=self.on)
