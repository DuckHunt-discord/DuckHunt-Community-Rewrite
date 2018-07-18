import discord
from discord.ext import commands
from cogs.helpers.checks import have_required_level


class Notify:
    """

    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def notify(self, ctx):
        """
        Add yourself to the notify role, so you'll get mentions about upcoming features and changes in the bot.
        There won't be that much mentions.
        """

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        role = discord.utils.get(ctx.message.guild.roles, name="Notify")

        if role in ctx.message.author.roles:
            # If a role in the user's list of roles matches one of those we're checking
            await ctx.message.author.remove_roles(role)
            await ctx.send_to("I removed your notify role.", delete_after=10)
        else:
            await ctx.message.author.add_roles(role)
            await ctx.send_to("I gave you the notify role.", delete_after=10)


def setup(bot):
    bot.add_cog(Notify(bot))
