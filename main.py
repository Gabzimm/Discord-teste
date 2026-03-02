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
        
        # Dicionário para controlar quais servidores já sincronizaram
        self.servidores_sincronizados = set()
    
    async def setup_hook(self):
        """NÃO sincroniza automaticamente - espera o on_ready"""
        print("🔄 Aguardando conexão com Discord para sincronizar comandos...")
    
    async def sincronizar_comandos(self, guild):
        """Sincroniza comandos para um servidor específico"""
        
        # Verificar se já sincronizou este servidor
        if guild.id in self.servidores_sincronizados:
            return False
        
        try:
            # Sincronizar comandos APENAS para este servidor
            comandos = await self.tree.sync(guild=guild)
            
            # Marcar como sincronizado
            self.servidores_sincronizados.add(guild.id)
            
            print(f"\n✅ Comandos sincronizados em: {guild.name}")
            print(f"   📋 {len(comandos)} comandos:")
            for cmd in comandos[:5]:  # Mostrar apenas os primeiros 5 para não poluir
                print(f"      → /{cmd.name}")
            if len(comandos) > 5:
                print(f"      ... e mais {len(comandos)-5} comandos")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao sincronizar {guild.name}: {e}")
            return False
    
    async def sincronizar_todos_servidores(self):
        """Sincroniza comandos para TODOS os servidores que o bot está"""
        
        print("\n" + "="*60)
        print("🔄 SINCRONIZANDO COMANDOS PARA TODOS OS SERVIDORES")
        print("="*60)
        
        total = 0
        for guild in self.guilds:
            if await self.sincronizar_comandos(guild):
                total += 1
        
        print("\n" + "="*60)
        print(f"✅ {total} servidores sincronizados com sucesso!")
        print(f"📊 Total de servidores: {len(self.guilds)}")
        print("="*60)
        
        return total

bot = MeuBot()

# ==================== COMANDOS ====================
@bot.tree.command(name="help", description="📖 Mostra todos os comandos disponíveis")
async def help_command(interaction: discord.Interaction):
    """Comando /help"""
    
    # Buscar comandos APENAS deste servidor
    comandos = bot.tree.get_commands(guild=interaction.guild)
    
    embed = discord.Embed(
        title="🤖 Comandos Disponíveis",
        description=f"Comandos do bot em **{interaction.guild.name}**:",
        color=discord.Color.blue()
    )
    
    # Agrupar comandos
    lista_comandos = []
    for cmd in sorted(comandos, key=lambda x: x.name):
        lista_comandos.append(f"`/{cmd.name}` - {cmd.description}")
    
    # Dividir em várias mensagens se necessário
    if len(lista_comandos) > 20:
        metade = len(lista_comandos) // 2
        embed.add_field(
            name="📋 Comandos (1/2)",
            value="\n".join(lista_comandos[:metade]),
            inline=False
        )
        embed.add_field(
            name="📋 Comandos (2/2)",
            value="\n".join(lista_comandos[metade:]),
            inline=False
        )
    else:
        embed.add_field(
            name="📋 Comandos",
            value="\n".join(lista_comandos) if lista_comandos else "Nenhum comando encontrado",
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(comandos)} comandos")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 Verifica a latência do bot")
async def ping_command(interaction: discord.Interaction):
    """Comando /ping"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latência: **{latency}ms**")

@bot.tree.command(name="status", description="📊 Mostra o status do bot")
async def status_command(interaction: discord.Interaction):
    """Comando /status"""
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=discord.Color.green()
    )
    
    embed.add_field(name="🤖 Nome", value=bot.user.name, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="📋 Comandos", value=len(bot.tree.get_commands()), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="ℹ️ Informações sobre o bot")
async def info_command(interaction: discord.Interaction):
    """Comando /info"""
    embed = discord.Embed(
        title="ℹ️ Sobre o Bot",
        description="Bot para comunidade Jugadores",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="📌 Versão", value="1.0.0", inline=True)
    embed.add_field(name="⚙️ Tipo", value="Slash Commands", inline=True)
    
    await interaction.response.send_message(embed=embed)

# EXEMPLO DE COMANDOS ADICIONAIS
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

@bot.tree.command(name="sync", description="🔄 Força sincronização dos comandos (admin)")
@app_commands.default_permissions(administrator=True)
async def sync_command(interaction: discord.Interaction):
    """Comando para forçar sincronização manual"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Sincronizar APENAS este servidor
        comandos = await bot.tree.sync(guild=interaction.guild)
        bot.servidores_sincronizados.add(interaction.guild.id)
        
        await interaction.followup.send(
            f"✅ Comandos sincronizados! {len(comandos)} comandos disponíveis.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print("\n" + "="*60)
    print("✅ BOT CONECTADO COM SUCESSO!")
    print("="*60)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print("="*60)
    
    # SINCRONIZAR AUTOMATICAMENTE TODOS OS SERVIDORES
    await bot.sincronizar_todos_servidores()
    
    # Status personalizado
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"/help | {len(bot.guilds)} servidores"
        )
    )

@bot.event
async def on_guild_join(guild):
    """Quando entra em um NOVO servidor"""
    print(f"\n📥 Entrou em NOVO servidor: {guild.name}")
    
    # Sincronizar comandos para o novo servidor automaticamente
    await bot.sincronizar_comandos(guild)
    
    # Enviar mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description=(
                    f"**Comandos disponíveis:**\n"
                    f"Digite **/** no chat para ver todos os comandos!\n\n"
                    f"📝 **Principais comandos:**\n"
                    f"• `/help` - Ver todos os comandos\n"
                    f"• `/ping` - Verificar latência\n"
                    f"• `/status` - Status do bot"
                ),
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

# ==================== KEEP-ALIVE ====================
async def keep_alive():
    """Servidor HTTP para manter o bot online"""
    app = web.Application()
    
    async def handle_home(request):
        return web.Response(
            text=f"""🤖 Bot Discord Online

📊 Status:
• Bot: {bot.user if bot.user else 'Conectando...'}
• Servidores: {len(bot.guilds)}
• Comandos: {len(bot.tree.get_commands())}

💡 Digite / no Discord para ver os comandos!""",
            content_type='text/plain'
        )
    
    async def handle_health(request):
        return web.json_response({
            "status": "online",
            "bot": str(bot.user) if bot.user else None,
            "guilds": len(bot.guilds),
            "commands": len(bot.tree.get_commands()),
            "sincronizados": len(bot.servidores_sincronizados),
            "timestamp": datetime.now().isoformat()
        })
    
    app.router.add_get('/', handle_home)
    app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"🌐 Keep-alive na porta {port}")
    return runner

# ==================== FUNÇÃO PRINCIPAL ====================
async def carregar_modulos():
    """Carrega os módulos do bot"""
    modulos = [
        'modules.sets',
        'modules.tickets',
        'modules.cargos',
        'modules.premios',
        'modules.painel_rec',
        'modules.limpeza',
    ]
    
    print("\n📦 Carregando módulos:")
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo}")
        except Exception as e:
            print(f"   ⚠️ {modulo}: {e}")

async def main():
    print("\n" + "="*60)
    print("🚀 INICIANDO BOT DISCORD")
    print("="*60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        sys.exit(1)
    
    # Iniciar keep-alive
    runner = await keep_alive()
    
    # Carregar módulos
    await carregar_modulos()
    
    # Iniciar bot
    try:
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado pelo usuário")
    finally:
        await runner.cleanup()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
