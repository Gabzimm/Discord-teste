import discord
from discord.ext import commands
import asyncio
import sys

class VozCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.canal_id = 1479257448010350673  # ID do canal WaveX
        self.verificar_pynacl()
        print("🔊 Sistema de Voz carregado!")
    
    def verificar_pynacl(self):
        """Verifica se PyNaCl está instalado"""
        try:
            import nacl
            print("✅ PyNaCl instalado corretamente")
        except ImportError:
            print("❌ PyNaCl NÃO está instalado!")
            print("   Execute: pip install PyNaCl")
    
    @commands.command(name="voz_conectar")
    async def voz_conectar(self, ctx):
        """!voz_conectar - Conecta ao canal WaveX"""
        
        # Verificar PyNaCl
        try:
            import nacl
        except ImportError:
            await ctx.send("❌ Biblioteca de voz não instalada! Contate o administrador.")
            return
        
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
            # Conectar
            await canal.connect()
            await ctx.send(f"✅ Conectado ao canal **{canal.name}**!")
        except discord.errors.Forbidden:
            await ctx.send("❌ Sem permissão para conectar neste canal!")
        except discord.errors.ClientException:
            await ctx.send("❌ Já estou conectado em algum lugar!")
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")
    
    @commands.command(name="voz_desconectar")
    async def voz_desconectar(self, ctx):
        """!voz_desconectar - Desconecta do canal"""
        
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("✅ Desconectado!")
        else:
            await ctx.send("❌ Não estou em nenhum canal!")
    
    @commands.command(name="voz_status")
    async def voz_status(self, ctx):
        """!voz_status - Mostra status"""
        
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.send(f"✅ Conectado em: {ctx.voice_client.channel.mention}")
        else:
            await ctx.send("❌ Desconectado")
    
    @commands.command(name="voz_instalar")
    @commands.has_permissions(administrator=True)
    async def voz_instalar(self, ctx):
        """!voz_instalar - Mostra comando para instalar PyNaCl (admin)"""
        
        embed = discord.Embed(
            title="🔧 Instalação do PyNaCl",
            description="Para corrigir o erro de voz, execute no terminal:",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Comando:",
            value="```bash\npip install PyNaCl==1.5.0\n```",
            inline=False
        )
        embed.add_field(
            name="Ou no Render:",
            value="1. Vá em Environment\n2. Adicione no requirements.txt:\n```\nPyNaCl==1.5.0\n```",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VozCog(bot))
    print("✅ Sistema de Voz configurado!")
