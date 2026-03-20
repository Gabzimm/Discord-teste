import discord
from discord.ext import commands
import asyncio

class VozCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.canal_id = 1479257448010350673  # ID do canal WaveX
        print("🔊 Sistema de Voz carregado!")
    
    @commands.command(name="entrar")
    async def entrar_call(self, ctx):
        """!entrar - Entra na call WaveX"""
        
        # Procurar o canal pelo ID
        canal = ctx.guild.get_channel(self.canal_id)
        
        if not canal:
            await ctx.send("❌ Canal WaveX não encontrado!")
            return
        
        # Verificar se já está conectado
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await asyncio.sleep(1)
        
        try:
            await canal.connect()
            await ctx.send(f"✅ Conectado ao canal **{canal.name}**!")
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")
    
    @commands.command(name="sair")
    async def sair_call(self, ctx):
        """!sair - Sai da call"""
        
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("✅ Desconectado!")
        else:
            await ctx.send("❌ Não estou em nenhum canal!")
    
    @commands.command(name="call")
    async def call_status(self, ctx):
        """!call - Mostra status da call"""
        
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.send(f"✅ Conectado em: {ctx.voice_client.channel.mention}")
        else:
            await ctx.send("❌ Desconectado")

async def setup(bot):
    await bot.add_cog(VozCog(bot))
    print("✅ Módulo de Voz configurado!")
