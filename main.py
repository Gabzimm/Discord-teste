from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import asyncio
import aiohttp
from aiohttp import web
import socket

# ==================== CONFIGURAÇÕES ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
    
    async def setup_hook(self):
        """Sincroniza comandos com UM SERVIDOR ESPECÍFICO (aparece na hora)"""
        
        # 🔴 COLOQUE AQUI O ID DO SEU SERVIDOR (CLIQUE COM BOTÃO DIREITO NO SERVIDOR > COPIAR ID)
        ID_DO_SERVIDOR = 1463243684861710361  # ← SUBSTITUA POR SEU ID REAL
        
        try:
            guild = discord.Object(id=ID_DO_SERVIDOR)
            
            # Limpar comandos antigos
            self.tree.clear_commands(guild=guild)
            
            # Copiar comandos globais para o servidor
            self.tree.copy_global_to(guild=guild)
            
            # Sincronizar com o servidor
            comandos = await self.tree.sync(guild=guild)
            
            print("\n" + "="*50)
            print("✅ COMANDOS SINCRONIZADOS COM SUCESSO!")
            print("="*50)
            print(f"📋 {len(comandos)} comandos registrados:")
            for cmd in comandos:
                print(f"   → /{cmd.name}")
            print("="*50)
            print("🔍 Digite / no Discord para ver os comandos!")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            print("Verifique se o ID do servidor está correto!")

bot = MeuBot()

# ==================== COMANDOS BÁSICOS ====================
@bot.tree.command(name="help", description="📖 Mostra todos os comandos")
async def help_command(interaction: discord.Interaction):
    """Comando /help"""
    comandos = bot.tree.get_commands()
    lista = "\n".join([f"`/{cmd.name}` - {cmd.description}" for cmd in comandos])
    
    embed = discord.Embed(
        title="🤖 Comandos Disponíveis",
        description=lista,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 Verifica a latência")
async def ping_command(interaction: discord.Interaction):
    """Comando /ping"""
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="sets", description="🎮 Sistema de sets")
async def sets_command(interaction: discord.Interaction):
    """Comando /sets"""
    await interaction.response.send_message("🎮 Comando sets executado!")

@bot.tree.command(name="tickets", description="🎫 Sistema de tickets")
async def tickets_command(interaction: discord.Interaction):
    """Comando /tickets"""
    await interaction.response.send_message("🎫 Comando tickets executado!")

@bot.tree.command(name="cargos", description="⚙️ Sistema de cargos")
async def cargos_command(interaction: discord.Interaction):
    """Comando /cargos"""
    await interaction.response.send_message("⚙️ Comando cargos executado!")

@bot.tree.command(name="premios", description="🏆 Sistema de prêmios")
async def premios_command(interaction: discord.Interaction):
    """Comando /premios"""
    await interaction.response.send_message("🏆 Comando premios executado!")

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print(f"\n✅ Bot conectado como: {bot.user}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print("\n🔍 Digite / no Discord para ver os comandos!")

# ==================== KEEP-ALIVE ====================
async def keep_alive():
    """Servidor HTTP simples para manter o bot online"""
    app = web.Application()
    
    async def handle(request):
        return web.Response(text="Bot Online - Comandos / ativos!")
    
    app.router.add_get('/', handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"🌐 Keep-alive na porta {port}")

# ==================== INÍCIO ====================
async def main():
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        return
    
    # Iniciar keep-alive
    asyncio.create_task(keep_alive())
    
    # Iniciar bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
