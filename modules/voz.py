import discord
from discord.ext import commands
import asyncio

class VozCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.canal_id = 1479257448010350673  # ID do canal WaveX
        self.conectando = False
        print("🔊 Sistema de Voz carregado!")
    
    @commands.command(name="entrar")
    async def entrar_call(self, ctx):
        """!entrar - Entra na call WaveX"""
        
        # Limpar conexões fantasmas no bot
        for voz in self.bot.voice_clients:
            if not voz.is_connected():
                await voz.disconnect(force=True)
        
        # Verificar se já está conectado de verdade
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.send(f"✅ Já estou conectado em **{ctx.voice_client.channel.name}**!")
            return
        
        if self.conectando:
            await ctx.send("⏳ Já estou tentando conectar, aguarde...")
            return
        
        canal = ctx.guild.get_channel(self.canal_id)
        
        if not canal:
            await ctx.send("❌ Canal WaveX não encontrado!")
            return
        
        self.conectando = True
        
        try:
            await ctx.send(f"🔊 Conectando ao canal **{canal.name}**...")
            
            # Desconectar forçado se houver conexão fantasma
            if ctx.voice_client:
                try:
                    await ctx.voice_client.disconnect(force=True)
                    await asyncio.sleep(1)
                except:
                    pass
            
            await canal.connect()
            self.bot.voz_conectada = True
            await ctx.send(f"✅ Conectado ao canal **{canal.name}**!")
            
        except discord.errors.ClientException as e:
            error_msg = str(e)
            if "Already connected" in error_msg:
                await ctx.send("⚠️ Parece que já estou conectado, mas não consigo detectar. Use `!sair` e `!voz_estado` para diagnosticar.")
            else:
                await ctx.send(f"❌ Erro: {error_msg}")
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")
        finally:
            self.conectando = False
    
    @commands.command(name="sair")
    async def sair_call(self, ctx):
        """!sair - Sai da call"""
        
        if not ctx.voice_client:
            await ctx.send("❌ Não estou em nenhum canal de voz!")
            return
        
        try:
            canal_nome = ctx.voice_client.channel.name
            await ctx.voice_client.disconnect(force=True)
            self.bot.voz_conectada = False
            await ctx.send(f"✅ Desconectado de **{canal_nome}**!")
        except Exception as e:
            await ctx.send(f"❌ Erro ao desconectar: {e}")
    
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
