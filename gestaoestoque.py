import tkinter as tk
from tkinter import messagebox, simpledialog
import sqlite3
import pandas as pd
import os

# Configurações principais
DB_EXCEL = "produtos.xlsx"
DB = "camara.db"

# Classe Produto
class Produto:
    def __init__(self, lote, nome, estoque, observacoes):
        self.lote = lote
        self.nome = nome
        self.estoque = estoque
        self.observacoes = observacoes

# Classe principal
class GestaoCamara:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestão CAX - C5")
        self.andar_atual = 2  # Começa no superior
        self.db_init()
        self.carregar_excel()
        self.interface()

    # Criar banco de dados
    def db_init(self):
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paletes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                posicao TEXT UNIQUE,
                lote TEXT,
                produto TEXT,
                estoque TEXT,
                observacoes TEXT,
                data_entrada TEXT
            )
        """)
        conn.commit()
        conn.close()

    # Carregar dados do Excel
    def carregar_excel(self):
        if not os.path.exists(DB_EXCEL):
            self.df_lotes = pd.DataFrame(columns=["Lote", "Produto", "Estoque", "Observacoes"])
            return
        self.df_lotes = pd.read_excel(DB_EXCEL, dtype=str).fillna("")

    # Gerar nome do rack com base na posição
    def nome_racks(self, andar, coluna, linha):
        if andar == 2:  # Superior - blocos de 3
            bloco = 4 - ((linha - 1) // 3)
        else:  # Inferior - blocos de 2
            bloco = 4 - ((linha - 1) // 2)
        return f"R{coluna}{andar}{bloco}"

    # Interface
    def interface(self):
        self.frame_top = tk.Frame(self.root)
        self.frame_top.pack(pady=10)
        
        self.lbl_andar = tk.Label(self.frame_top, text=f"{'Segundo Andar' if self.andar_atual == 2 else 'Primeiro Andar'}", font=("Arial", 12, "bold"))
        self.lbl_andar.pack(side=tk.LEFT, padx=5)

        btn_trocar = tk.Button(self.frame_top, text="Alternar Andar", command=self.mudar_andar)
        btn_trocar.pack(side=tk.LEFT, padx=5)

        btn_pesquisar = tk.Button(self.frame_top, text="Pesquisar", command=self.pesquisar_produto)
        btn_pesquisar.pack(side=tk.LEFT, padx=5)

        btn_atualizar = tk.Button(self.frame_top, text="Atualizar Dados", command=self.atualizar_dados_produtos)
        btn_atualizar.pack(side=tk.LEFT, padx=5)
    
        self.frame_mapa = tk.Frame(self.root)
        self.frame_mapa.pack()

        self.desenhar_mapa()

    # Mudar andares
    def mudar_andar(self):
        self.andar_atual = 1 if self.andar_atual == 2 else 2
        self.lbl_andar.config(text=f"{'Segundo Andar' if self.andar_atual == 2 else 'Primeiro Andar'}")
        for widget in self.frame_mapa.winfo_children():
            widget.destroy()
        self.desenhar_mapa()

    # Desenhar mapa 
    def desenhar_mapa(self):
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT posicao, lote, produto FROM paletes")
        ocupadas = {pos: (lote, produto) for pos, lote, produto in cur.fetchall()}
        conn.close()

        if self.andar_atual == 2:
            colunas, linhas, bloco_tam = 9, 12, 3
        else:
            colunas, linhas, bloco_tam = 9, 8, 2

        for c in range(1, colunas + 1):
            for l in range(1, linhas + 1):
                rack_nome = self.nome_racks(self.andar_atual, c, l)
                pos_id = f"{rack_nome}_{l}"

                # Cor do bloco alternada
                bloco_id = (l - 1) // bloco_tam
                cor = "#cce5ff" if bloco_id % 2 == 0 else "white"

                # Texto do botão (apenas rack e lote)
                if pos_id in ocupadas:
                    lote, _ = ocupadas[pos_id]
                    texto = f"{rack_nome}\n{lote}"
                    btn = tk.Button(self.frame_mapa, text=texto, width=12, height=2,
                                    bg="red", command=lambda p=pos_id: self.mostrar_detalhes(p))
                else:
                    texto = f"{rack_nome}\n"
                    btn = tk.Button(self.frame_mapa, text=texto, width=12, height=2,
                                    bg=cor, command=lambda p=pos_id: self.registrar_entrada(p))

                btn.grid(row=l, column=c, padx=(5 if (l - 1) % bloco_tam == 0 else 1),
                         pady=(5 if (l - 1) % bloco_tam == 0 else 1))

    # Registrar entrada de produto
    def registrar_entrada(self, posicao):
        lote = simpledialog.askstring("Entrada de Produto", "Digite o número do lote:")
        if not lote:
            return

        # Verificar se lote já está alocado
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT posicao FROM paletes WHERE lote = ?", (lote,))
        if cur.fetchone():
            messagebox.showwarning("Aviso", f"O lote {lote} já está alocado em outra posição.")
            conn.close()
            return

        # Buscar no Excel
        produto_info = self.df_lotes[self.df_lotes["Lote"] == lote]
        if produto_info.empty:
            # Registo manual
            p = Produto(lote, nome="", estoque="", observacoes="")
        else:
            produto = produto_info.iloc[0]
            p = Produto(produto["Lote"], produto["Produto"], produto["Estoque"], produto["Observacoes"])

        cur.execute("""
            INSERT INTO paletes (posicao, lote, produto, estoque, observacoes, data_entrada)
            VALUES (?, ?, ?, ?, ?, date('now'))
        """, (posicao, p.lote, p.nome, p.estoque, p.observacoes))
        conn.commit()
        conn.close()

        self.mudar_andar()
        self.mudar_andar()

    # Mostrar detalhes
    def mostrar_detalhes(self, posicao):
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT lote, produto, estoque, observacoes FROM paletes WHERE posicao = ?", (posicao,))
        dados = cur.fetchone()
        conn.close()

        if not dados:
            return

        lote, produto, estoque, obs = dados
        msg = f"Lote: {lote}\nProduto: {produto}\nEstoque: {estoque}\nObservações: {obs}"
        if messagebox.askyesno("Detalhes", msg + "\n\nDeseja remover este lote?"):
            self.remover_lote(posicao)

    # Remover lote
    def remover_lote(self, posicao):
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("DELETE FROM paletes WHERE posicao = ?", (posicao,))
        conn.commit()
        conn.close()

        self.mudar_andar()
        self.mudar_andar()

    # Pesquisa por lote ou nome
    def pesquisar_produto(self):
        termo = simpledialog.askstring("Pesquisar", "Digite o lote ou parte do nome do produto:")
        if not termo:
            return
        termo = termo.lower()

        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT posicao, lote, produto FROM paletes")
        resultados = [(p, l, prod) for p, l, prod in cur.fetchall()
                      if termo in l.lower() or termo in prod.lower()]
        conn.close()

        if not resultados:
            messagebox.showinfo("Pesquisa", "Nenhum resultado encontrado.")
            return

        msg = "\n".join([f"{p} - {l} - {prod}" for p, l, prod in resultados])
        messagebox.showinfo("Resultados da Pesquisa", msg)

    # Atualizar dados com base no Excel
    def atualizar_dados_produtos(self):
        self.carregar_excel()

        if self.df_lotes.empty:
            messagebox.showwarning("Aviso", "O arquivo de Excel está vazio ou não foi encontrado.")
            return

        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        cur.execute("SELECT id, lote FROM paletes")
        registros = cur.fetchall()

        alterados = 0
        for reg_id, lote in registros:
            produto_info = self.df_lotes[self.df_lotes["Lote"] == str(lote)]
            if not produto_info.empty:
                produto = produto_info.iloc[0]
                cur.execute("""
                    UPDATE paletes
                    SET produto = ?, estoque = ?, observacoes = ?
                    WHERE id = ?
                """, (produto["Produto"], produto["Estoque"], produto["Observacoes"], reg_id))
                alterados += 1

        conn.commit()
        conn.close()

        self.mudar_andar()
        self.mudar_andar()

        messagebox.showinfo("Atualização Concluída", f"{alterados} registros foram atualizados com sucesso!")

# Executar o programa
if __name__ == "__main__":
    root = tk.Tk()
    app = GestaoCamara(root)
    root.mainloop()
