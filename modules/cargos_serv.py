import discord
from discord.ext import commands
import asyncio
from datetime import datetime

class CargosServidorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mensagens_ativas = {}
        print("✅ Sistema de Cargos carregado!")
    
    @commands.command(name="cargos")
    async def cargos_comando(self, ctx):
        """!cargos - Mostra todos os cargos do servidor"""
        
        # Pegar todos os cargos (exceto @everyone)
        cargos = [role for role in ctx.guild.roles if role.name != "@everyone"]
        
        # Ordenar por posição (do mais alto para o mais baixo)
        cargos.sort(key=lambda r: r.position, reverse=True)
        
        if not cargos:
            await ctx.send("❌ Nenhum cargo encontrado!")
            return
        
        embed = discord.Embed(
            title="📋 Cargos do Servidor",
            description=f"Total de **{len(cargos)}** cargos encontrados",
            color=discord.Color.blue()
        )
        
        lista_cargos = []
        for i, cargo in enumerate(cargos, 1):
            lista_cargos.append(f"`{i:02d}.` {cargo.mention} • Posição `#{i}` na hierarquia")
        
        # Dividir em blocos de 15 para não estourar limite
        for i in range(0, len(lista_cargos), 15):
            bloco = lista_cargos[i:i+15]
            embed.add_field(
                name=f"📌 Cargos (Ordem Hierárquica)",
                value="\n".join(bloco),
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CargosServidorCog(bot))
    print("✅ Módulo de Cargos configurado!")
