import logging

from discord.ext import commands


class CustomContext(commands.Context):

    def __init__(self, **attrs):
        super().__init__(**attrs)

    @property
    def logger(self):
        # Copy that to log
        if self.channel:
            cname = self.channel.name
        else:
            cname = "PRIVATE_MESSAGE"

        extra = {"channelname": f"#{cname}", "userid": f"{self.author.id}", "username": f"{self.author.name}#{self.author.discriminator}"}
        logger = logging.LoggerAdapter(self.bot.base_logger, extra)
        return logger

    async def send_to(self, message, user=None, **kwargs):
        if user is None:
            user = self.author

        message = f"{user.mention} > {message}"

        await self.send(message, **kwargs)
