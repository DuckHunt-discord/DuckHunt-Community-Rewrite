import collections
import datetime
import logging
import re
from typing import Union

import discord
from discord.ext import commands

from cogs.helpers import context
from cogs.helpers.mod_actions import Kick, Ban, Unban, Softban, Warn, Note
from cogs.helpers.checks import get_level

DEBUG = False
BAD_WORDS = ['nigga', 'fuck', 'cunt', 'dick', 'cock']


class CheckMessage:
    def __init__(self, bot, message: discord.Message):
        self.bot = bot
        self.message = message
        self.multiplicator = 1
        self.score = 0

        self.old_multiplicator = self.multiplicator
        self.old_score = self.score

        self.logs = []

        self.invites = []

        self.debug(f"MESSAGE : {message.content:.100}")

    @property
    def total(self):
        return self.multiplicator * self.score

    @property
    def old_total(self):
        return self.old_multiplicator * self.old_score

    @property
    def invites_code(self):
        return [i.code for i in self.invites]

    @property
    def logs_for_discord(self):
        return "```\n" + "\n".join(self.logs) + "\n```"

    def debug(self, s):
        fs = f"[s={self.score:+.2f} ({self.score - self.old_score:+.2f})," \
             f" m={self.multiplicator:+.2f} ({self.multiplicator - self.old_multiplicator:+.2f})," \
             f" t={self.total:+.2f} ({self.total - self.old_total:+.2f})] > " + s

        if DEBUG:
            if self.message.channel:
                cname = self.message.channel.name
            else:
                cname = "PRIVATE_MESSAGE"

            extra = {"channelname": f"#{cname}", "userid": f"{self.message.author.id}", "username": f"{self.message.author.name}#{self.message.author.discriminator}"}
            logger = logging.LoggerAdapter(self.bot.base_logger, extra)
            logger.debug(f"AM " + fs)

        self.logs.append(fs)
        self.old_score = self.score
        self.old_multiplicator = self.multiplicator



class AutoMod:
    """
    Custom on_message parser to detect and prevent things like spam, AThere/everyone mentions...
    """

    def __init__(self, bot):
        self.bot = bot
        self.invites_regex = re.compile(r'discord(?:app\.com|\.gg)[\/invite\/]?(?:(?!.*[Ii10OolL]).[a-zA-Z0-9]{5,6}|[a-zA-Z0-9\-]{2,32})')
        self.message_history = collections.defaultdict(lambda: collections.deque(maxlen=7))  # Member -> collections.deque(maxlen=7)

    async def get_invites(self, message: str):

        invites = self.invites_regex.findall(message)

        return list(set(invites)) or None

    async def get_invites_count(self, check_message: CheckMessage):
        message_str = check_message.message.content
        invites = await self.get_invites(message_str)

        if invites is None:
            return 0
        else:
            total = 0
            for invite in invites:
                check_message.debug(f"Checking invite code : {invite}")

                try:
                    invite_obj = await self.bot.get_invite(invite)
                    if invite_obj.guild.id not in [195260081036591104, 449663867841413120]:
                        check_message.debug(f">> Detected invite code for untrusted server : {invite_obj.code} (server : {invite_obj.guild.name} - {invite_obj.guild.id})")

                        check_message.invites.append(invite_obj)
                        total += 1
                    else:
                        check_message.debug(f">> Detected invite code for trusted server : {invite_obj.code}")
                except discord.errors.NotFound:
                    check_message.debug(f">> Invalid invite code")

                    continue

            return total


    @commands.command()
    @commands.guild_only()
    async def automod_debug(self, ctx, *, message_str):
        ctx.message.content = message_str
        cm = await self.check_message(ctx.message, act=False)
        await ctx.send_to(cm.logs_for_discord)

    async def check_message(self, message, act=True) -> Union[CheckMessage, None]:
        await self.bot.wait_until_ready()

        author = message.author

        if author.bot:
            return None  # ignore messages from other bots

        if message.guild is None:
            return None  # ignore messages from PMs

        check_message = CheckMessage(self.bot, message)
        author_level = get_level(check_message.message.author)

        if author.status is discord.Status.offline:
            check_message.multiplicator += 0.15
            check_message.debug("Author is offline (probably invisible)")

        if author.created_at > datetime.datetime.now() - datetime.timedelta(days=7):
            check_message.multiplicator += 0.75
            check_message.debug("Author account is less than a week old")

        if author.joined_at > datetime.datetime.now() - datetime.timedelta(days=1):
            check_message.multiplicator += 0.5
            check_message.debug("Author account joined less than a day ago")

        if author.is_avatar_animated():
            check_message.multiplicator -= 0.75
            check_message.debug("Author account is nitro'd (or at least I can detect an animated avatar)")

        if len(author.roles) > 2:  # Role duckies is given by default
            check_message.multiplicator -= 0.10
            check_message.debug("Author account have a role in the server")

        if author_level == 0:
            check_message.multiplicator += 0.25
            check_message.debug("Author is bot-banned")
        elif author_level >= 2:
            check_message.multiplicator -= 0.75
            check_message.debug("Author is trusted on the server")

        if check_message.multiplicator <= 0:
            check_message.debug("Multiplicator is <= 0, exiting without getting score")
            return check_message  # Multiplicator too low!

        check_message.debug("Multiplicator calculation done")

        ## Multiplicator calculation done!

        total_letters = len(message.content)
        total_captial_letters = sum(1 for c in message.content if c.isupper())
        caps_percentage = total_captial_letters / total_letters if total_letters > 0 else 1  # If no letters, then 100% caps.

        if caps_percentage >= 0.7 and total_letters > 10:
            check_message.score += 1
            check_message.debug(f"Message is written in CAPS LOCK (% of caps: {caps_percentage} —  total length: {total_letters})")

        #if len(message.embeds) >= 1:
        #    check_message.score += 5
        #    check_message.debug(f"Message from a USER contain an EMBED !? (Used to circumvent content blocking)")

        if "@everyone" in message.content and not message.mention_everyone:
            check_message.score += 1
            check_message.debug(f"Message contains an ATeveryone that discord did not register as a ping (failed attempt)")

        mentions = set(message.mentions)
        if len(mentions) > 3:
            check_message.score += 1
            m_list = [a.name + '#' + a.discriminator for a in mentions]
            check_message.debug(f"Message mentions more than 3 people ({m_list})")

        if await self.get_invites_count(check_message) >= 1 and not message.channel.id == 195260377150259211:
            check_message.score += 2.5
            check_message.debug(f"Message contains invite(s) ({check_message.invites_code})")

        repeat = self.message_history[check_message.message.author].count(check_message.message.content)
        if repeat >= 3:
            check_message.score += 0.25 * repeat
            check_message.debug(f"Message was repeated by the author {repeat} times")

        bad_words_in_message = {b_word for b_word in BAD_WORDS if b_word in check_message.message.content.lower()}
        bad_words_count = len(bad_words_in_message)

        if bad_words_count >= 1:
            check_message.score += 0.15 * bad_words_count
            check_message.debug(f"Message contains {bad_words_count} bad words ({', '.join(bad_words_in_message)})")

        if not check_message.message.content.lower().startswith(("dh", "!", "?", "§", "t!", ">", "<", "-")) or len(check_message.message.content) > 30\
                and check_message.message.content.lower() not in ['yes', 'no', 'maybe', 'hey', 'hi', 'hello', 'oui', 'non', 'bonjour', '\o', 'o/', ':)', ':D', ':(', 'ok', 'this', 'that', 'yup']\
                and act:
            # Not a command or something
            self.message_history[check_message.message.author].append(check_message.message.content)  # Add content for repeat-check later.

        check_message.debug("Score calculation done")
        check_message.debug(f"Total for message is {check_message.total}, applying actions if any")

        ctx = await self.bot.get_context(message, cls=context.CustomContext)

        # Do we need to delete the message ?
        if check_message.total >= 2:
            check_message.debug(f"Deleting message because score **{check_message.total}** >= 2")
            try:
                if act:
                    a = Note(ctx, author, "Automod deleted a message from this user. Logs: \n" + check_message.logs_for_discord)
                    await a.do()
                    await check_message.message.delete()

            except discord.errors.NotFound:
                check_message.debug(f"Message already deleted!")

            try:
                await check_message.message.author.send(f"Heya!\n"
                                                        f"I deleted your message in {check_message.message.channel.mention} because you tripped my auto detection ratio. "
                                                        f"This system is brand new, and probably need to be improved.\n"
                                                        f"\n"
                                                        f"If you feel this is an error, please report the following logs to Eyesofcreeper#0001: \n"
                                                        f"Thanks for your cooperation and remember to maintain a safe space!")
                await check_message.message.author.send(f"{check_message.logs_for_discord:.1990}")

            except discord.errors.Forbidden:
                pass
        else:  # Too low to do anything else
            return check_message

        # That's moderation acts, where the bot grabs his BIG HAMMER and throw it in the user face
        # Warning
        if check_message.total >= 2.5:
            check_message.debug(f"Warning user because score **{check_message.total}** >= 2.5")
            if act:
                a = Warn(ctx, author, "Automatic action from automod. Logs: \n" + check_message.logs_for_discord)
                await a.do()
        elif check_message.total >= 3.5:

            # Softban / Kick ?
            # Ban after ?
            pass  # Need to fine-tune the system before adding this

        ctx.logger.info("Automod acted on a message, logs follow.")
        ctx.logger.info("\n".join(check_message.logs))
        return check_message

    async def on_message(self, message):
        await self.check_message(message)

    async def on_message_edit(self, _, message):
        if not len(message.content): return
        await self.check_message(message)


def setup(bot):
    bot.add_cog(AutoMod(bot))
