# modules/Termos-site.py
"""
Módulo de site de termos para WaveX
Adiciona um endpoint /termos com os termos do servidor
"""

from datetime import datetime
from aiohttp import web
import discord
from discord.ext import commands
import os

class TermosSite:
    def __init__(self, bot):
        self.bot = bot
        self.app = None
        self.runner = None
        self.site = None
    
    async def setup_routes(self, app):
        """Configurar rotas do site"""
        
        async def handle_termos(request):
            """Página principal de termos"""
            html = f"""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>WaveX - Termos de Serviço</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
                        background: linear-gradient(135deg, #1a1a1a 0%, #2d1b3d 100%);
                        color: #ffffff;
                        line-height: 1.6;
                        min-height: 100vh;
                    }}
                    
                    /* Header com imagem */
                    .hero {{
                        background: linear-gradient(135deg, rgba(106, 13, 173, 0.9) 0%, rgba(62, 13, 118, 0.95) 100%);
                        padding: 60px 20px;
                        text-align: center;
                        border-bottom: 3px solid #9b4dff;
                    }}
                    
                    .hero-image {{
                        width: 100%;
                        max-width: 800px;
                        height: auto;
                        border-radius: 20px;
                        margin-bottom: 30px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
                        border: 2px solid #9b4dff;
                    }}
                    
                    .hero h1 {{
                        font-size: 3em;
                        margin-bottom: 10px;
                        background: linear-gradient(135deg, #ffffff 0%, #9b4dff 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                    }}
                    
                    .hero p {{
                        font-size: 1.2em;
                        color: #e0e0e0;
                    }}
                    
                    /* Container principal */
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 40px 20px;
                    }}
                    
                    /* Seções */
                    .section {{
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 20px;
                        padding: 30px;
                        margin-bottom: 30px;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(155, 77, 255, 0.3);
                        transition: transform 0.3s ease, box-shadow 0.3s ease;
                    }}
                    
                    .section:hover {{
                        transform: translateY(-5px);
                        box-shadow: 0 10px 30px rgba(155, 77, 255, 0.2);
                        border-color: #9b4dff;
                    }}
                    
                    .section-title {{
                        font-size: 1.8em;
                        margin-bottom: 20px;
                        color: #9b4dff;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        border-left: 4px solid #9b4dff;
                        padding-left: 20px;
                    }}
                    
                    .section-content {{
                        padding-left: 30px;
                        color: #e0e0e0;
                    }}
                    
                    .section-content p {{
                        margin-bottom: 15px;
                    }}
                    
                    .section-content ul {{
                        list-style: none;
                        padding-left: 20px;
                    }}
                    
                    .section-content li {{
                        margin-bottom: 10px;
                        position: relative;
                        padding-left: 25px;
                    }}
                    
                    .section-content li:before {{
                        content: "▹";
                        color: #9b4dff;
                        position: absolute;
                        left: 0;
                        font-weight: bold;
                    }}
                    
                    /* Destaque para avisos importantes */
                    .warning {{
                        background: linear-gradient(135deg, rgba(255, 70, 70, 0.1) 0%, rgba(155, 77, 255, 0.1) 100%);
                        border-left: 4px solid #ff4646;
                        padding: 20px;
                        margin-top: 20px;
                        border-radius: 10px;
                    }}
                    
                    .warning-title {{
                        color: #ff4646;
                        font-weight: bold;
                        margin-bottom: 10px;
                        font-size: 1.2em;
                    }}
                    
                    .tax-box {{
                        background: rgba(155, 77, 255, 0.1);
                        border: 1px solid #9b4dff;
                        border-radius: 15px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    
                    .tax-box h3 {{
                        color: #9b4dff;
                        margin-bottom: 15px;
                    }}
                    
                    .tax-item {{
                        padding: 10px;
                        margin: 10px 0;
                        background: rgba(0,0,0,0.2);
                        border-radius: 8px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        flex-wrap: wrap;
                    }}
                    
                    .tax-value {{
                        color: #9b4dff;
                        font-weight: bold;
                        font-size: 1.1em;
                    }}
                    
                    /* Footer */
                    .footer {{
                        text-align: center;
                        padding: 40px 20px;
                        background: rgba(0, 0, 0, 0.5);
                        margin-top: 40px;
                        border-top: 1px solid rgba(155, 77, 255, 0.3);
                    }}
                    
                    .footer p {{
                        margin: 10px 0;
                        color: #888;
                    }}
                    
                    .footer a {{
                        color: #9b4dff;
                        text-decoration: none;
                        transition: color 0.3s ease;
                    }}
                    
                    .footer a:hover {{
                        color: #ffffff;
                    }}
                    
                    /* Botão de voltar */
                    .back-button {{
                        display: inline-block;
                        background: linear-gradient(135deg, #9b4dff 0%, #6a0dad 100%);
                        color: white;
                        padding: 12px 30px;
                        border-radius: 50px;
                        text-decoration: none;
                        margin-top: 20px;
                        font-weight: bold;
                        transition: transform 0.3s ease;
                        border: none;
                        cursor: pointer;
                    }}
                    
                    .back-button:hover {{
                        transform: scale(1.05);
                    }}
                    
                    /* Responsividade */
                    @media (max-width: 768px) {{
                        .hero h1 {{
                            font-size: 2em;
                        }}
                        
                        .section {{
                            padding: 20px;
                        }}
                        
                        .section-title {{
                            font-size: 1.4em;
                        }}
                        
                        .section-content {{
                            padding-left: 15px;
                        }}
                        
                        .tax-item {{
                            flex-direction: column;
                            align-items: flex-start;
                            gap: 8px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="hero">
                    <img src="https://cdn.discordapp.com/attachments/1296527396337619006/1484690785369722880/Design_sem_nome_3.png?ex=69c5bd0b&is=69c46b8b&hm=4951e70ad546fed4e2bc9fa9b260d4f23adfaa5e567136a7fbf81dbc5ed9871f" 
                         alt="WaveX Banner" 
                         class="hero-image">
                    <h1>📜 WaveX - Termos de Serviço</h1>
                    <p>Última atualização: {datetime.now().strftime('%d/%m/%Y')}</p>
                </div>
                
                <div class="container">
                    <!-- Política Antifraude -->
                    <div class="section">
                        <h2 class="section-title">🛡️ Política Antifraude</h2>
                        <div class="section-content">
                            <p><strong>1.1</strong> Qualquer tentativa de fraude, golpe ou atividade suspeita resultará no banimento imediato e permanente do usuário, sem aviso prévio.</p>
                            <p><strong>1.2</strong> A loja se reserva o direito de analisar e investigar atividades consideradas suspeitas, podendo tomar as medidas cabíveis, inclusive junto às autoridades competentes.</p>
                            <p><strong>1.3</strong> É proibida a revenda, redistribuição ou compartilhamento dos produtos sem autorização prévia. O descumprimento resultará na perda de acesso aos serviços e possível encerramento da conta.</p>
                        </div>
                    </div>
                    
                    <!-- Entrega de Produtos -->
                    <div class="section">
                        <h2 class="section-title">🤖 Entrega de Produtos</h2>
                        <div class="section-content">
                            <p><strong>2.1</strong> O prazo de entrega é de até 72 horas (3 dias) após a confirmação do pagamento.</p>
                            <p><strong>2.2</strong> A entrega será realizada com base nas informações fornecidas pelo cliente, sendo de sua total responsabilidade garantir que estejam corretas e atualizadas.</p>
                            <p><strong>2.3</strong> A loja realiza apenas a configuração básica inicial do produto. Configurações adicionais são de responsabilidade do cliente.</p>
                        </div>
                    </div>
                    
                    <!-- Pagamentos e Serviços -->
                    <div class="section">
                        <h2 class="section-title">💰 Pagamentos e Serviços</h2>
                        <div class="section-content">
                            <p><strong>3.1</strong> Os serviços serão iniciados somente após a confirmação do pagamento.</p>
                            <p><strong>3.2</strong> Todos os pedidos são considerados finais após a entrega.</p>
                            <p><strong>3.3</strong> O não pagamento poderá resultar na suspensão automática dos serviços, sem aviso prévio.</p>
                            <p><strong>3.4</strong> Após 5 (cinco) dias sem pagamento, o serviço poderá ser suspenso. Para reativação, será necessário o pagamento do valor pendente.</p>
                        </div>
                    </div>
                    
                    <!-- Garantia e Suporte Inicial -->
                    <div class="section">
                        <h2 class="section-title">📌 Garantia e Suporte Inicial</h2>
                        <div class="section-content">
                            <p><strong>4.1</strong> A loja garante suporte e ajustes relacionados ao produto pelo prazo de até 7 (sete) dias após a entrega.</p>
                            <p><strong>4.2</strong> Durante esse período, serão realizados ajustes necessários para o funcionamento adequado do produto, desde que dentro do escopo original.</p>
                            <p><strong>4.3</strong> Após esse prazo, novos ajustes ou suporte poderão não estar incluídos.</p>
                        </div>
                    </div>
                    
                    <!-- Uso e Conduta -->
                    <div class="section">
                        <h2 class="section-title">⚠️ Uso e Conduta</h2>
                        <div class="section-content">
                            <p><strong>5.1</strong> Apenas clientes com pagamento confirmado poderão solicitar alterações no produto.</p>
                            <p><strong>5.2</strong> É proibido o uso dos serviços para práticas ilegais ou abusivas, incluindo preconceito, discriminação, ameaças, conteúdo adulto, spam ou flood.</p>
                            <p><strong>5.3</strong> O descumprimento das regras poderá resultar em suspensão ou banimento permanente, sem aviso prévio.</p>
                        </div>
                    </div>
                    
                    <!-- Taxas e Cobranças -->
                    <div class="section">
                        <h2 class="section-title">🚨 Avisos Importantes (Taxas e Cobranças)</h2>
                        <div class="section-content">
                            <div class="tax-box">
                                <div class="tax-item">
                                    <span>🔄 Troca de servidor:</span>
                                    <span class="tax-value">Primeira alteração gratuita | R$5,00 por solicitação adicional</span>
                                </div>
                                <div class="tax-item">
                                    <span>⚡ Reativação de serviço:</span>
                                    <span class="tax-value">R$5,50 + valor pendente</span>
                                </div>
                                <div class="tax-item">
                                    <span>📊 Reincidência (3ª ocorrência):</span>
                                    <span class="tax-value">Taxa em dobro</span>
                                </div>
                                <div class="tax-item">
                                    <span>🔧 Ajustes após garantia:</span>
                                    <span class="tax-value">Sujeito à cobrança conforme análise</span>
                                </div>
                            </div>
                            <div class="warning">
                                <div class="warning-title">⚠️ Importante</div>
                                <p>Em caso de reincidência, após 2 (duas) reativações por falta de pagamento, a partir da 3ª ocorrência a taxa de reativação será aplicada em dobro, como forma de compensar custos operacionais e administrativos recorrentes.</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Disposições Gerais -->
                    <div class="section">
                        <h2 class="section-title">📌 Disposições Gerais</h2>
                        <div class="section-content">
                            <p><strong>6.1</strong> A loja se reserva o direito de alterar estes termos a qualquer momento, sem aviso prévio.</p>
                            <p><strong>6.2</strong> O uso dos serviços implica na aceitação total destes termos.</p>
                            <p><strong>6.3</strong> O suporte deve ser acionado exclusivamente através do sistema de tickets no Discord.</p>
                        </div>
                    </div>
                    
                    <!-- Botão de voltar -->
                    <div style="text-align: center; margin-top: 40px;">
                        <a href="/" class="back-button">🏠 Voltar para a página inicial</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2024 WaveX - Todos os direitos reservados</p>
                    <p>Desenvolvido para a comunidade WaveX | Suporte via Discord</p>
                    <p><a href="/termos">Termos de Serviço</a> | <a href="/api">API Status</a></p>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html, content_type='text/html')
        
        app.router.add_get('/termos', handle_termos)
        print("📄 Rota /termos configurada com sucesso!")

async def setup(bot):
    """Setup do módulo de termos"""
    termos_site = TermosSite(bot)
    
    # Tentar obter o app do keep_alive existente
    if hasattr(bot, 'keep_alive') and bot.keep_alive and bot.keep_alive.app:
        print("🔗 Conectando termos ao servidor keep-alive existente...")
        await termos_site.setup_routes(bot.keep_alive.app)
    else:
        print("⚠️ Servidor keep-alive não encontrado. Criando servidor independente...")
        # Criar servidor independente se necessário
        from aiohttp import web
        app = web.Application()
        await termos_site.setup_routes(app)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        port = int(os.environ.get('PORT', 10000))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        print(f"🌐 Site de termos rodando na porta {port}")
        print(f"📄 Acesse: http://localhost:{port}/termos ou seu domínio/termos")
    
    print("✅ Módulo Termos-site carregado com sucesso!")
