from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd
import os
from datetime import datetime
import json

app = FastAPI()

# --- CORREÇÃO DE CAMINHOS ---
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
CAMINHO_EXCEL = os.path.join(DIRETORIO_BASE, 'base_estoque.xlsx')
CAMINHO_LOG = '/tmp/log.txt' # <-- Única mudança de caminho para o Vercel não travar

def carregar_estoque_do_excel(nome_arquivo):
    estoque_dict = {}
    materiais_dict = {} # Novo dicionário para guardar a relação MATERIAL -> DESCRICAO
    
    if not os.path.exists(nome_arquivo):
        hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensagem_erro = f"[{hora_atual}] ERRO: O ficheiro '{nome_arquivo}' não foi encontrado.\n"
        
        print(mensagem_erro)
        print("A carregar base de dados de teste temporária...")
        
        with open(CAMINHO_LOG, "a", encoding="utf-8") as f:
            f.write(mensagem_erro)
            
        estoque_teste = {
            "PRODUTO TESTE (Sem Excel)": ["839", "835", "832"],
            "BATATA TESTE 100G": ["970", "969"],
            "MIOJO TESTE": ["312"],
            "ARROZ TESTE": ["800", "801", "802", "803"]
        }
        materiais_teste = {
            "1001": "PRODUTO TESTE (Sem Excel)",
            "1002": "BATATA TESTE 100G",
            "1003": "MIOJO TESTE",
            "1004": "ARROZ TESTE"
        }
        return estoque_teste, materiais_teste
        
    try:
        df = pd.read_excel(nome_arquivo)
        df.columns = [col.upper().strip() for col in df.columns]
        
        # Agora exigimos também a coluna MATERIAL
        if 'DESCRICAO' not in df.columns or 'ENDERECO' not in df.columns or 'MATERIAL' not in df.columns:
            msg_colunas = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERRO: Colunas 'MATERIAL', 'DESCRICAO' ou 'ENDERECO' não encontradas.\n"
            print(msg_colunas)
            with open(CAMINHO_LOG, "a", encoding="utf-8") as f:
                f.write(msg_colunas)
            return {}, {}

        df['DESCRICAO'] = df['DESCRICAO'].fillna("SEM DESCRIÇÃO").astype(str)
        df['ENDERECO'] = df['ENDERECO'].fillna("").astype(str)
        df['MATERIAL'] = df['MATERIAL'].fillna("").astype(str)
        
        for index, row in df.iterrows():
            produto = row['DESCRICAO'].strip()
            endereco = row['ENDERECO'].strip()
            material = row['MATERIAL'].strip()
            
            if endereco.endswith('.0'):
                endereco = endereco[:-2]
            if material.endswith('.0'):
                material = material[:-2]
                
            # Popula o dicionário de busca por material
            if material and produto:
                materiais_dict[material.upper()] = produto

            if not endereco:
                continue
                
            if produto not in estoque_dict:
                estoque_dict[produto] = set()
            
            estoque_dict[produto].add(endereco)

        for prod in estoque_dict:
            estoque_dict[prod] = list(estoque_dict[prod])
            
        print(f"✅ Sucesso! {len(estoque_dict)} produtos carregados do Excel.")
        return estoque_dict, materiais_dict
        
    except Exception as e:
        msg_excecao = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERRO AO LER EXCEL: {str(e)}\n"
        print(msg_excecao)
        with open(CAMINHO_LOG, "a", encoding="utf-8") as f:
            f.write(msg_excecao)
        return {}, {}

estoque, materiais = carregar_estoque_do_excel(CAMINHO_EXCEL)

@app.get("/", response_class=HTMLResponse)
async def index():
    produtos_qtd = {p: len(ends) for p, ends in estoque.items()}
    qtds_unicas = sorted(list(set(produtos_qtd.values())))
    opcoes_qtd_html = "".join([f'<option value="{q}">{q} Endereço(s)</option>' for q in qtds_unicas])
    
    produtos = sorted(list(estoque.keys()))
    opcoes_html = "".join([f'<option value="{p}">{p}</option>' for p in produtos])
    
    produtos_json = json.dumps(produtos_qtd)
    materiais_json = json.dumps(materiais) # Envia o dicionário de materiais para o JavaScript
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-PT">
    <head>
        <meta charset="UTF-8">
        <title>Maquete do Depósito Interativo</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f9; padding: 20px; margin: 0; }}
            
            .controles-container {{ display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-top: 10px; }}
            select, input[type="text"] {{ padding: 12px; font-size: 15px; border-radius: 6px; border: 1px solid #ccc; cursor: pointer; }}
            select {{ width: 300px; }}
            input[type="text"] {{ width: 250px; cursor: text; }}
            
            #info {{ margin-top: 15px; margin-bottom: 25px; font-size: 18px; font-weight: bold; color: #333; height: 25px; }}
            
            .warehouse-wrapper {{ 
                background-color: #b0b0b0; 
                padding: 30px; 
                border-radius: 8px; 
                display: inline-block; 
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
                white-space: nowrap; 
            }}
            .flex-row {{ display: flex; flex-direction: row; gap: 30px; }}
            .block {{ display: flex; flex-direction: row; background: #999; padding: 2px; height: fit-content; }}
            .col {{ display: flex; flex-direction: column; }}
            
            .rack {{ 
                background-color: #ff0000; 
                color: black; 
                font-size: 10px; 
                font-weight: bold;
                width: 32px; 
                height: 26px; 
                margin: 1px; 
                display: flex; 
                flex-direction: column;
                align-items: center; 
                justify-content: center; 
                transition: all 0.3s ease;
                border: 1px solid #cc0000;
                line-height: 1.1;
                box-sizing: border-box;
            }}
            .rack.special {{ height: 100%; width: 50px; font-size: 14px; flex-direction: row; }}
            .rack.vazio {{ background-color: #c62828 !important; color: #ffcdd2 !important; font-size: 8px; border-color: #b71c1c; opacity: 0.8; }}
            
            .main-aisle {{
                background: repeating-linear-gradient(45deg, #FFEA00, #FFEA00 20px, #FFD600 20px, #FFD600 40px);
                height: 35px;
                margin: 25px 0;
                border-top: 3px solid #333;
                border-bottom: 3px solid #333;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: inset 0 0 10px rgba(0,0,0,0.3);
                font-weight: 900;
                color: #222;
                letter-spacing: 8px;
                font-size: 14px;
                text-transform: uppercase;
                border-radius: 4px;
            }}
            
            .highlight {{ 
                background-color: #00FF00 !important; 
                color: black !important; 
                transform: scale(1.4); 
                border: 2px solid #005500; 
                box-shadow: 0 0 10px #00FF00; 
                z-index: 100; 
                position: relative; 
            }}
            .dim {{ opacity: 0.15; filter: grayscale(80%); }}
        </style>
    </head>
    <body>
        <h1>Visão Geral do Depósito 📦</h1>
        
        <div class="controles-container">
            <input type="text" id="buscaMaterial" placeholder="Buscar código do Material..." oninput="buscarPorMaterial()">

            <select id="qtdSelect" onchange="filtrarProdutos()">
                <option value="">Filtrar por qtd. endereços (Todos)</option>
                {opcoes_qtd_html}
            </select>

            <select id="produtoSelect" onchange="destacarProduto()">
                <option value="">Selecione um Produto para localizar...</option>
                {opcoes_html}
            </select>
        </div>
        
        <div id="info"></div>

        <div class="warehouse-wrapper">
            <div style="display: flex; justify-content: flex-end; padding-right: 170px; margin-bottom: 20px;">
                <div class="block" id="topTopRow"></div>
            </div>
            <div id="topRow" class="flex-row"></div>
            <div class="main-aisle">🚧 CORREDOR PRINCIPAL 🚧</div>
            <div id="bottomRow" class="flex-row" style="align-items: flex-start;"></div>
        </div>

        <script>
            const produtosData = {produtos_json};
            const materiaisData = {materiais_json}; // Carrega o mapeamento no front-end

            // Nova Função: Busca o código do material enquanto o utilizador digita
            function buscarPorMaterial() {{
                const codigo = document.getElementById("buscaMaterial").value.trim().toUpperCase();
                
                // Se o código digitado existir na nossa base
                if (materiaisData[codigo]) {{
                    const produtoEncontrado = materiaisData[codigo];

                    // 1. Limpa o filtro de quantidade para garantir que o produto vai aparecer na lista
                    document.getElementById("qtdSelect").value = "";
                    filtrarProdutos(); 

                    // 2. Força a seleção do produto encontrado
                    const produtoSelect = document.getElementById("produtoSelect");
                    produtoSelect.value = produtoEncontrado;

                    // 3. Destaca no mapa
                    destacarProduto();
                }}
            }}

            function filtrarProdutos() {{
                const qtdSelecionada = document.getElementById("qtdSelect").value;
                const produtoSelect = document.getElementById("produtoSelect");
                const produtoAnterior = produtoSelect.value;

                produtoSelect.innerHTML = '<option value="">Selecione um Produto para localizar...</option>';
                let produtosFiltrados = Object.keys(produtosData);

                if (qtdSelecionada !== "") {{
                    produtosFiltrados = produtosFiltrados.filter(p => produtosData[p] == qtdSelecionada);
                }}

                produtosFiltrados.sort();

                produtosFiltrados.forEach(p => {{
                    let opt = document.createElement("option");
                    opt.value = p;
                    opt.innerText = p;
                    produtoSelect.appendChild(opt);
                }});

                if (produtosFiltrados.includes(produtoAnterior)) {{
                    produtoSelect.value = produtoAnterior; 
                }} else {{
                    destacarProduto(); 
                }}
            }}

            function r(start, end) {{
                let arr = [];
                if (start <= end) {{
                    for (let i = start; i <= end; i++) arr.push(i);
                }} else {{
                    for (let i = start; i >= end; i--) arr.push(i);
                }}
                return arr;
            }}

            const v4 = ['vazio', 'vazio', 'vazio', 'vazio'];

            const topRowData = [
                {{ t: 'single', d: [...v4, ...r(312, 300)] }},
                {{ t: 'double', l: [...v4, ...r(313, 323), 801], r: [...v4, ...r(334, 324), 802] }},
                {{ t: 'double', l: [...v4, ...r(335, 345), 803], r: [...v4, ...r(356, 346), 804] }},
                {{ t: 'single', d: [...v4, ...r(357, 367), 805] }},
                {{ t: 'double', l: [840, ...r(382, 368), 806], r: [841, ...r(383, 397), 807] }},
                {{ t: 'double', l: [842, ...r(412, 398), 808], r: [843, ...r(413, 427), 809] }},
                {{ t: 'single', d: [844, ...r(442, 428), 810] }},
                {{ t: 'special', id: 800 }},
                {{ t: 'single', d: [845, ...r(457, 443), 811] }},
                {{ t: 'ring', 
                  left: [846, ...r(458, 466)], 
                  top: r(847, 853), 
                  bottom: r(824, 830), 
                  right: [854, ...r(878, 871), 831],
                  tail: [812, ...r(467, 471)], 
                  arm: r(839, 832) 
                }},
                {{ t: 'spacer', width: '30px' }}, 
                {{ t: 'single', d: r(879, 885) }}
            ];

            const bottomRowData = [
                {{ t: 'single', d: r(590, 602) }},
                {{ t: 'double', l: [822, ...r(589, 578)], r: [821, ...r(566, 577)] }},
                {{ t: 'double', l: [820, ...r(565, 554)], r: [819, ...r(542, 553)] }},
                {{ t: 'single', d: [818, ...r(541, 531)] }},
                {{ t: 'double', l: [817, ...r(520, 530)], r: [816, ...r(519, 509)] }},
                {{ t: 'double', l: [815, ...r(498, 508)], r: [814, ...r(497, 487)] }},
                {{ t: 'single', d: [813, ...r(476, 486)] }},
                {{ t: 'loose_racks', ids: [475, 474], ml: '40px' }}, 
                {{ t: 'loose_racks', ids: [473], ml: '45px' }},
                {{ t: 'single', d: [472], ml: '35px' }} 
            ];

            function getRackHtml(id) {{
                if (id === 'vazio') {{
                    return `<div class="rack vazio" data-ids="">Vazio</div>`;
                }}

                let display = id;
                let allIds = [id];

                if (id >= 300 && id <= 499) {{
                    let pair = id - 200;
                    display = `${{pair}}<br>${{id}}`;
                    allIds.push(pair);
                }} else if (id >= 500 && id <= 570) {{
                    let pair = id + 400;
                    display = `${{id}}<br>${{pair}}`;
                    allIds.push(pair);
                }}
                return `<div class="rack" data-ids="${{allIds.join(',')}}">${{display}}</div>`;
            }}

            function renderCol(arr) {{
                return `<div class="col">` + arr.map(getRackHtml).join('') + `</div>`;
            }}

            function renderRow(arr) {{
                return `<div style="display: flex; flex-direction: row;">` + arr.map(getRackHtml).join('') + `</div>`;
            }}

            function renderBlock(b) {{
                let ml = b.ml ? `margin-left: ${{b.ml}};` : '';
                
                if (b.t === 'single') return `<div class="block" style="${{ml}}">` + renderCol(b.d) + `</div>`;
                if (b.t === 'double') return `<div class="block" style="${{ml}}">` + renderCol(b.l) + renderCol(b.r) + `</div>`;
                if (b.t === 'special') return `<div class="block" style="${{ml}}"><div class="rack special" data-ids="${{b.id}}">${{b.id}}</div></div>`;
                if (b.t === 'spacer') return `<div style="width: ${{b.width}};"></div>`;
                
                if (b.t === 'loose_racks') {{
                    return `<div class="block" style="flex-direction: row; height: fit-content; ${{ml}}">` + 
                           b.ids.map(getRackHtml).join('') + 
                           `</div>`;
                }}
                
                if (b.t === 'ring') {{
                    return `
                    <div class="block" style="flex-direction: column; background: #999; padding: 2px;">
                        <div style="display: flex; justify-content: center; margin-left: 34px; margin-right: 34px;">
                            ${{renderRow(b.top)}}
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            ${{renderCol(b.left)}}
                            <div style="flex-grow: 1; background: #fff; margin: 0 2px;"></div>
                            ${{renderCol(b.right)}}
                        </div>
                        <div style="display: flex; justify-content: center; margin-left: 34px; margin-right: 34px;">
                            ${{renderRow(b.bottom)}}
                        </div>
                        <div style="display: flex; flex-direction: row;">
                            ${{b.tail ? renderCol(b.tail) : ''}}
                            ${{b.arm ? renderRow(b.arm) : ''}}
                        </div>
                    </div>`;
                }}
            }}

            document.getElementById('topTopRow').innerHTML = renderRow(r(870, 855));
            document.getElementById('topRow').innerHTML = topRowData.map(renderBlock).join('');
            document.getElementById('bottomRow').innerHTML = bottomRowData.map(renderBlock).join('');

            function destacarProduto() {{
                const produto = document.getElementById("produtoSelect").value;
                const infoDiv = document.getElementById("info");
                const racks = document.querySelectorAll(".rack");

                racks.forEach(r => r.classList.remove("highlight", "dim"));

                if (!produto) {{
                    infoDiv.innerText = "";
                    return;
                }}

                fetch(`/buscar/${{encodeURIComponent(produto)}}`)
                    .then(response => response.json())
                    .then(data => {{
                        const enderecosProduto = data.enderecos; 
                        
                        const enderecosTexto = enderecosProduto.join(", ");
                        infoDiv.innerText = `🟢 Produto: ${{produto}} | Localizações do Sistema: ${{enderecosTexto}}`;

                        let scrollFeito = false;

                        racks.forEach(r => {{
                            const idsStr = r.getAttribute("data-ids");
                            if(!idsStr) return; 

                            const idsDaCaixa = idsStr.split(",");
                            const isMatch = enderecosProduto.some(end => idsDaCaixa.includes(String(end)));

                            if (isMatch) {{
                                r.classList.add("highlight");
                                
                                if (!scrollFeito) {{
                                    r.scrollIntoView({{ behavior: "smooth", block: "center", inline: "center" }});
                                    scrollFeito = true;
                                }}
                            }} else {{
                                r.classList.add("dim");
                            }}
                        }});
                    }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/buscar/{produto:path}")
async def buscar(produto: str):
    enderecos = estoque.get(produto, [])
    return JSONResponse(content={"produto": produto, "enderecos": enderecos})
