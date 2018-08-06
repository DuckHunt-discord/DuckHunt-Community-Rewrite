# -*- coding: utf-8 -*-
# !/usr/bin/env python3.5

"""

"""
import datetime
import json

import discord


class Roles:

    def __init__(self, bot):
        self.bot = bot
        self.root_dir = "users/"

    @property
    def channel(self):
        channel = self.bot.get_channel(297750761365045249)
        return channel

    async def get_and_assign_roles(self, member):
        try:
            file_name = str(member.id) + ".json"
            with open(self.root_dir + file_name, "r") as infile:
                m_roles = set(map(int, json.load(infile)))
        except FileNotFoundError:
            return []

        roles = []

        for role in member.guild.roles:
            if role.id in m_roles and "everyone" not in role.name:
                roles.append(role)
        roles_names = [r.name for r in roles]

        self.bot.logger.info(f"Adding role(s) {roles_names} to {member.name}, as requested by get_and_assign_roles in the file {self.root_dir}{file_name}")
        await member.add_roles(*roles, reason="Automatic roles restore")

        return roles_names

    async def save_roles(self, member):
        file_name = str(member.id) + ".json"
        roles = member.roles
        roles_ids = [r.id for r in roles]  # .remove("322707763992199170") #Sans @everyone
        with open(self.root_dir + file_name, "w") as outfile:
            json.dump(roles_ids, outfile)
        return [r.name for r in roles]

    async def on_member_join(self, member):
        roles_name = await self.get_and_assign_roles(member)

        channel = self.channel
        embed = discord.Embed()
        embed.colour = discord.Colour.green()
        embed.title = "User {u} joined".format(u=member.name + "#" + member.discriminator)
        embed.timestamp = datetime.datetime.now()
        embed.set_author(name=member.id, icon_url=member.avatar_url)
        embed.description = f"Restored roles : {roles_name}"
        await channel.send(embed=embed)

    async def on_member_remove(self, member):
        roles_name = await self.save_roles(member)
        channel = self.channel

        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "User {u} left".format(u=member.name + "#" + member.discriminator)
        embed.timestamp = datetime.datetime.now()
        embed.set_author(name=member.id, icon_url=member.avatar_url)
        embed.description = f"Saved roles : {roles_name}"
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Roles(bot))
