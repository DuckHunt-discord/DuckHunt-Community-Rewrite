"""
These are checks to see if some commands can be executed by users.
"""

import discord
from discord.ext import commands


def get_level(user: discord.Member):
    roles = [r.id for r in user.roles]
    # [195260081036591104, 356082143304351744, 195261796330897408, 306076806371344385]

    if 306076806371344385 in roles:  # Owner
        return 5
    elif 195261182729256961 in roles:  # Admin
        return 4
    elif 285752516589649922 in roles:  # Moderator
        return 3
    elif 304949336989630466 in roles:  # Proficient
        return 2
    elif 423556200915927050 in roles:  # Website Maintainer
        return 2
    elif 195261712201416705 in roles:  # Web interface Developer
        return 2
    elif 195261796330897408 in roles:  # Bot Developer
        return 2
    elif 270012143007432705 in roles:  # Translator
        return 2
    elif 306078530712633346 in roles:  # NoBoat
        return 0
    else:
        return 1


class PermissionsError(commands.CheckFailure):
    def __init__(self, required, current):
        self.required = required
        self.current = current


def have_required_level(required: int = 0):
    async def predicate(ctx):
        level = get_level(ctx.message.author)
        cond = level >= required

        ctx.logger.debug(f"Check for level required returned {cond} (c={level}, r={required})")
        if cond:
            return True
        else:
            raise PermissionsError(required=required, current=level)

    return commands.check(predicate)
