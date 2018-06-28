#!/usr/bin/env python3.6
# This is DuckHunt Community V2 (Rewrite)
# **You have to use it with the rewrite version of discord.py**
# You can install it using
# pip install -U git+https://github.com/Rapptz/discord.py@rewrite#egg=discord.py[voice]
# You also have to use python 3.6 to run this
# Have fun !
# The doc for d.py rewrite is here : http://discordpy.readthedocs.io/en/rewrite/index.html

print("Loading...")

# First, load the logging modules, they will be useful for later

from cogs.helpers.init_logger import init_logger
base_logger, logger = init_logger()

# Setting up asyncio to use uvloop if possible, a faster implementation on the event loop
import asyncio

try:
    # noinspection PyUnresolvedReferences
    import uvloop
except ImportError:
    logger.warning("Using the not-so-fast default asyncio event loop. Consider installing uvloop.")
    pass
else:
    logger.info("Using the fast uvloop asyncio event loop")
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Importing the discord API warpper
import discord
import discord.ext.commands as commands

# Load some essentials modules
import traceback
import collections
import json

logger.debug("Creating a bot instance of commands.AutoShardedBot")

from cogs.helpers import context


class DuckHunt(commands.AutoShardedBot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

        self.commands_used = collections.Counter()
        self.admins = [138751484517941259]
        self.base_logger, self.logger = base_logger, logger

        # Load credentials so they can be used later
        with open("credentials.json", "r") as f:
            credentials = json.load(f)

        self.token = credentials["token"]

    async def on_message(self, message):
        if message.author.bot:
            return  # ignore messages from other bots

        ctx = await self.get_context(message, cls=context.CustomContext)
        if ctx.prefix is not None:
            await self.invoke(ctx)

    async def on_command(self, ctx):
        bot.commands_used[ctx.command.name] += 1
        ctx.logger.info(f"<{ctx.command}> {ctx.message.clean_content}")

    async def on_ready(self):
        logger.info("We are all set, on_ready was fired! Yeah!")
        logger.info(f"I see {len(self.guilds)} guilds")

    async def on_command_error(self, context, exception):
        if isinstance(exception, discord.ext.commands.errors.CommandNotFound):
            return
        elif isinstance(exception, discord.ext.commands.errors.MissingRequiredArgument):
            await context.send_to(":x: A required argument is missing.")  # Here is the command documentation : \n```\n", language) + context.command.__doc__ +
            # "\n```")
            return
        # elif isinstance(exception, checks.PermissionsError):
        #    await self.send_message(ctx=context, message=":x: You are not a server admin")
        #    return

        elif isinstance(exception, discord.ext.commands.errors.CheckFailure):
            return
        elif isinstance(exception, discord.ext.commands.errors.CommandOnCooldown):
            if context.message.author.id in self.admins:
                await context.reinvoke()
                return
            else:

                await context.send_to("You are on cooldown :(, try again in {seconds} seconds".format(seconds=round(exception.retry_after, 1)))
                return
        logger.error('Ignoring exception in command {}:'.format(context.command))
        logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))


bot = DuckHunt(command_prefix=["c!", "§"], case_insensitive=True)

logger.debug("Loading cogs : ")

######################
#                 |  #
#   ADD COGS HERE |  #
#                 V  #
# ###############   ##

cogs = ['cogs.basics', ]

for extension in cogs:
    try:
        bot.load_extension(extension)
        logger.debug(f"> {extension} loaded!")
    except Exception as e:
        logger.exception('> Failed to load extension {}\n{}: {}'.format(extension, type(e).__name__, e))

logger.info("Everything seems fine, we are now connecting to discord.")

try:
    # bot.loop.set_debug(True)
    bot.loop.run_until_complete(bot.start(bot.token))
except KeyboardInterrupt:
    pass
finally:
    game = discord.Game(name=f"Restarting...")
    bot.loop.run_until_complete(bot.change_presence(status=discord.Status.dnd, activity=game))

    bot.loop.run_until_complete(bot.logout())

    asyncio.sleep(3)
    bot.loop.close()

