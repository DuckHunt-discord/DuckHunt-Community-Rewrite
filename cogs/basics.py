import datetime

import discord
from discord.ext import commands
from cogs.helpers.checks import have_required_level

class Basics:
    """
    Really basic commands of the bot

    Normally one liners or misc stuff that can't go anywhere else.
    """
    def __init__(self, bot):
        self.bot = bot


    def get_bot_uptime(self):
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h} hours, {m} minutes, and {s} seconds'

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    @commands.command()
    @have_required_level(1)
    async def uptime(self, ctx):
        """
        Tells you how long the bot has been up for.
        """
        await ctx.send_to('Uptime: **{}**'.format(self.get_bot_uptime()))

    @commands.command()
    @have_required_level(6)
    async def level(self):
        """
        Nobody can do this anyway, the required permission is too high.
        """
        pass

    @commands.command()
    @have_required_level(2)
    async def webinterface_roles(self, ctx):
        roles = {
            '$admins'                        : 'Owner',
            '$moderators'                    : 'Moderator',
            '$translators'                   : 'Translator',
            '$bug_hunters'                   : 'Bug Hunters',
            '$proficients'                   : 'Proficient',
            '$partners'                      : 'Partner',
            '$donators'                      : 'Donator',
            '$enigma_event_winners_june_2018': 'DuckEnigma Event Winner 2018'
        }

        member_list = sorted(ctx.guild.members, key=lambda u: u.name)



        for role_var in sorted(roles.keys()):
            role_name = roles[role_var]

            role = discord.utils.get(ctx.guild.roles, name=role_name)
            php_code = '```'
            php_code += f"{role_var} = array(\n"

            for member in member_list:
                if role in member.roles:
                    php_code += f"{member.id}, // {member.name}#{member.discriminator}\n"

            php_code += ");\n\n"

            php_code += '```'

            await ctx.send(php_code)







def setup(bot):
    bot.add_cog(Basics(bot))
