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
import traceback
from typing import Optional

# ==================== VERIFICAÇÃO DE INSTÂNCIA ÚNICA ====================
def verificar_instancia_unica():
    try:
        if sys.platform == "win32":
            import win32event, win32api, winerror
            mutex_name = "Bot_Jugadores_Slash_Unico"
            mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                print("❌ ERRO: Já existe uma instância do bot rodando!")
                return False
            return True
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind('\0bot_jugadores_slash_unico')
            return True
    except Exception as e:
        if sys.platform != "win32" and isinstance(e, socket.error):
            print("❌ ERRO: Já existe uma instância do bot rodando!")
            return False
        return True

if not verificar_instancia_unica():
    sys.exit(1)

# ==================== CONFIGURAÇÕES DO BOT ====================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = False

class SlashBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )
        
        # Dicionário para tracking de uso dos comandos
        self.comando_uso = {}
        
    async def setup_hook(self):
        """Configuração inicial"""
        print("\n" + "=" * 60)
        print("🔄 CONFIGURANDO SLASH COMMANDS")
        print("=" * 60)
        
        # Carregar todos os módulos
        print("\n📦 Carregando módulos...")
        await self.carregar_modulos()
        
        # Sincronizar comandos com o Discord
        print("\n🔄 Sincronizando comandos...")
        
        try:
            # Sincronização global
            print("   → Sincronizando globalmente...")
            global_commands = await self.tree.sync()
            print(f"   ✅ {len(global_commands)} comandos sincronizados globalmente!")
            
        except Exception as e:
            print(f"   ❌ Erro na sincronização: {e}")
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("✅ CONFIGURAÇÃO CONCLUÍDA")
        print("=" * 60)
    
    async def carregar_modulos(self):
        """Carrega todos os módulos do bot"""
        modulos = [
            'modules.sets',
            'modules.tickets',
            'modules.config_cargos',
            'modules.cargos',
            'modules.painel_rec',
            'modules.limpeza',
            'modules.painel_hierarquia',
            'modules.premios',
        ]
        
        carregados = 0
        for modulo in modulos:
            try:
                await self.load_extension(modulo)
                print(f"   ✅ {modulo}")
                carregados += 1
            except Exception as e:
                print(f"   ❌ {modulo}: {e}")
        
        print(f"\n   📊 Total: {carregados}/{len(modulos)} módulos carregados")
    
    def registrar_uso_comando(self, comando_nome: str, interaction: discord.Interaction) -> None:
        """Registra uso de comando para estatísticas"""
        guild_id = interaction.guild_id if interaction.guild_id else 0
        
        if guild_id not in self.comando_uso:
            self.comando_uso[guild_id] = {}
        
        if comando_nome not in self.comando_uso[guild_id]:
            self.comando_uso[guild_id][comando_nome] = 0
        
        self.comando_uso[guild_id][comando_nome] += 1

bot = SlashBot()

# ==================== KEEP-ALIVE SERVER ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
    
    async def start(self):
        try:
            self.app = web.Application()
            
            async def handle_home(request: web.Request) -> web.Response:
                return web.Response(
                    text=f"""🤖 Bot Discord Online - Slash Commands

📊 Status:
• Bot: {bot.user if bot.user else 'Desconectado'}
• Servidores: {len(bot.guilds)}
• Comandos: {len(bot.tree.get_commands()) if bot.tree else 0}

💡 No Discord, digite / para ver os comandos!""",
                    content_type='text/plain'
                )
            
            async def handle_health(request: web.Request) -> web.Response:
                return web.json_response({
                    "status": "online",
                    "bot": str(bot.user) if bot.user else None,
                    "guilds": len(bot.guilds),
                    "commands": len(bot.tree.get_commands()) if bot.tree else 0,
                    "timestamp": datetime.now().isoformat()
                })
            
            self.app.router.add_get('/', handle_home)
            self.app.router.add_get('/health', handle_health)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            port = int(os.getenv('PORT', 8080))
            site = web.TCPSite(self.runner, '0.0.0.0', port)
            await site.start()
            
            print(f"🌐 Keep-alive na porta {port}")
            
        except Exception as e:
            print(f"⚠️ Erro keep-alive: {e}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()

keep_alive = KeepAliveServer()

# ==================== FUNÇÃO PARA REGISTRAR USO (SEM DECORATOR) ====================
async def registrar_uso_comando(interaction: discord.Interaction) -> None:
    """Registra uso de comando (chame esta função no início de cada comando)"""
    if interaction.command:
        bot.registrar_uso_comando(interaction.command.name, interaction)

# ==================== COMANDOS PRINCIPAIS ====================

@bot.tree.command(name="help", description="📖 Mostra todos os comandos disponíveis")
async def help_command(interaction: discord.Interaction, comando: Optional[str] = None):
    """Comando de ajuda principal"""
    await registrar_uso_comando(interaction)
    
    if comando:
        # Buscar comando específico
        cmd = None
        for command in bot.tree.get_commands():
            if command.name.lower() == comando.lower():
                cmd = command
                break
        
        if not cmd:
            await interaction.response.send_message(
                f"❌ Comando `{comando}` não encontrado!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📖 Ajuda: /{cmd.name}",
            description=cmd.description or "Sem descrição",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Listar todos os comandos
    embed = discord.Embed(
        title=f"🤖 Comandos do {bot.user.name}",
        description="Digite **/** no chat para ver todos os comandos com autocomplete!",
        color=discord.Color.purple()
    )
    
    # Agrupar por categoria
    categorias = {}
    for cmd in bot.tree.get_commands():
        categoria = cmd.module.split('.')[-1].capitalize() if cmd.module else "Geral"
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(cmd)
    
    for categoria, comandos in sorted(categorias.items()):
        lista = [f"`/{cmd.name}` - {cmd.description or '...'}" for cmd in sorted(comandos, key=lambda x: x.name)[:5]]
        if len(comandos) > 5:
            lista.append(f"*... e mais {len(comandos)-5} comandos*")
        
        embed.add_field(name=f"📁 {categoria}", value="\n".join(lista), inline=False)
    
    embed.set_footer(text=f"Total: {len(bot.tree.get_commands())} comandos")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 Verifica a latência do bot")
async def ping_command(interaction: discord.Interaction):
    """Comando ping"""
    await registrar_uso_comando(interaction)
    
    latency = round(bot.latency * 1000)
    
    # Escolher cor baseada na latência
    if latency < 200:
        cor = discord.Color.green()
        status = "✅ Excelente"
    elif latency < 500:
        cor = discord.Color.orange()
        status = "⚠️ Razoável"
    else:
        cor = discord.Color.red()
        status = "❌ Ruim"
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latência:** {latency}ms\n**Status:** {status}",
        color=cor
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="📊 Mostra status detalhado do bot")
async def status_command(interaction: discord.Interaction):
    """Comando status"""
    await registrar_uso_comando(interaction)
    
    embed = discord.Embed(
        title="🤖 Status do Bot",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🏷️ Nome", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="📊 Comandos", value=len(bot.tree.get_commands()), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="comandos_stats", description="📈 Mostra estatísticas de uso dos comandos")
@app_commands.default_permissions(administrator=True)
async def stats_comandos(interaction: discord.Interaction):
    """Mostra quais comandos são mais usados"""
    await registrar_uso_comando(interaction)
    
    guild_id = interaction.guild_id
    
    if guild_id not in bot.comando_uso or not bot.comando_uso[guild_id]:
        await interaction.response.send_message(
            "📊 Nenhum comando foi usado ainda neste servidor!",
            ephemeral=True
        )
        return
    
    # Ordenar por uso
    top_comandos = sorted(bot.comando_uso[guild_id].items(), key=lambda x: x[1], reverse=True)[:10]
    
    embed = discord.Embed(
        title="📊 Comandos Mais Usados",
        description=f"No servidor **{interaction.guild.name}**",
        color=discord.Color.gold()
    )
    
    stats = "\n".join([f"**{i}.** `/{cmd}` - {count} uso(s)" 
                      for i, (cmd, count) in enumerate(top_comandos, 1)])
    
    embed.add_field(name="📈 Top 10", value=stats, inline=False)
    
    total_usos = sum(bot.comando_uso[guild_id].values())
    embed.set_footer(text=f"Total de usos: {total_usos}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="debug_slash", description="🔧 Diagnóstico dos slash commands (admin)")
@app_commands.default_permissions(administrator=True)
async def debug_slash(interaction: discord.Interaction):
    """Comando de diagnóstico para verificar registro dos comandos"""
    
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="🔧 Diagnóstico Slash Commands",
        description="Verificando registro dos comandos...",
        color=discord.Color.blue()
    )
    
    # 1. Comandos locais (no bot)
    local_commands = bot.tree.get_commands()
    embed.add_field(
        name="📦 Comandos no Bot",
        value=f"**Total:** {len(local_commands)}\n" +
              ", ".join([f"`{cmd.name}`" for cmd in local_commands[:10]]) +
              ("..." if len(local_commands) > 10 else ""),
        inline=False
    )
    
    # 2. Comandos registrados globalmente
    try:
        global_commands = await bot.tree.fetch_commands()
        embed.add_field(
            name="🌍 Comandos Globais",
            value=f"**Total:** {len(global_commands)}\n" +
                  ", ".join([f"`{cmd.name}`" for cmd in global_commands[:10]]) +
                  ("..." if len(global_commands) > 10 else ""),
            inline=False
        )
    except Exception as e:
        embed.add_field(name="🌍 Comandos Globais", value=f"❌ Erro: {e}", inline=False)
    
    # 3. Comandos neste servidor
    try:
        guild_commands = await bot.tree.fetch_commands(guild=interaction.guild)
        embed.add_field(
            name=f"📋 Comandos em {interaction.guild.name}",
            value=f"**Total:** {len(guild_commands)}\n" +
                  ", ".join([f"`{cmd.name}`" for cmd in guild_commands[:10]]) +
                  ("..." if len(guild_commands) > 10 else ""),
            inline=False
        )
    except Exception as e:
        embed.add_field(name="📋 Comandos no Servidor", value=f"❌ Erro: {e}", inline=False)
    
    # 4. Dicas para aparecer em "Utilizados com frequência"
    embed.add_field(
        name="💡 Dicas para aparecer em 'Utilizados com frequência'",
        value="• Use os comandos regularmente\n"
              "• Quanto mais usar, mais rápido eles aparecem\n"
              "• O Discord aprende com seu padrão de uso\n"
              "• Pode levar alguns dias para o algoritmo se ajustar",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

# ==================== EVENTOS ====================

@bot.event
async def on_ready():
    print("\n" + "=" * 60)
    print("✅ BOT CONECTADO!")
    print("=" * 60)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print(f"📊 Comandos Registrados: {len(bot.tree.get_commands())}")
    print("=" * 60)
    
    # Listar comandos
    print("\n📋 Comandos disponíveis:")
    for cmd in sorted(bot.tree.get_commands(), key=lambda x: x.name):
        print(f"   /{cmd.name} - {cmd.description}")
    
    print("\n💡 Dica: No Discord, digite / para ver os comandos!")
    print("=" * 60)
    
    # Status personalizado
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"/help | {len(bot.guilds)} servidores"
        )
    )

@bot.event
async def on_guild_join(guild: discord.Guild):
    """Quando entra em novo servidor"""
    print(f"📥 Novo servidor: {guild.name} ({guild.id})")
    
    # Enviar mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Olá!",
                description=(
                    f"Obrigado por me adicionar ao **{guild.name}**!\n\n"
                    f"📝 **Como usar:**\n"
                    f"• Digite **/** no chat\n"
                    f"• Meus comandos aparecerão automaticamente\n"
                    f"• Use **/help** para ver todos os comandos\n\n"
                    f"⚡ Os comandos podem levar alguns minutos para aparecer!"
                ),
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

# ==================== TRATAMENTO DE ERROS ====================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Tratamento de erros"""
    
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏰ Calma! Espere {error.retry_after:.1f}s",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Sem permissão!",
            ephemeral=True
        )
    else:
        print(f"❌ Erro: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Erro: {error}",
                ephemeral=True
            )

# ==================== FUNÇÃO PRINCIPAL ====================

async def main():
    print("\n" + "=" * 60)
    print("🚀 INICIANDO BOT SLASH COMMANDS")
    print("=" * 60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        sys.exit(1)
    
    # Iniciar keep-alive
    try:
        await keep_alive.start()
    except Exception as e:
        print(f"⚠️ Erro keep-alive: {e}")
    
    # Conectar ao Discord
    try:
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado")
    finally:
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
