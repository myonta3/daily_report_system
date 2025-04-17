def submit_report(self, preview_window):
        """レポートをLINE WORKSに送信し、データベースに保存"""
        # LINE WORKSにメッセージを送信
        message = self.report_data["content"]
        send_success = self.send_lineworks_message(message)
        
        if send_success:
            # データベースに保存
            self.save_report_to_db()
            
            # プレビューウィンドウを閉じる
            preview_window.destroy()
            
            # 完了メッセージ
            messagebox.showinfo("送信完了", "日報を送信しました")
            
            # メイン画面に戻る
            self.show_system_status()
    
    def save_report_to_db(self):
        """レポートをデータベースに保存"""
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            
            # データ挿入
            cursor.execute("""
                INSERT INTO reports (report_type, report_date, report_time, name, content)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.report_data["type"],
                self.report_data["date"],
                self.report_data["time"],
                self.report_data["name"],
                self.report_data["content"]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            messagebox.showerror("データベースエラー", f"レポートの保存中にエラーが発生しました: {str(e)}")
    
    def format_morning_report(self, data):
        """朝の日報のフォーマット"""
        message = f"{data['date']} スケジュール\n\n"
        message += f"氏名：{data['name']}\n\n"
        message += f"勉強科目：{data['subject']}\n"
        message += f"取得目標：{data['goal']}\n\n"
        message += f"本日の目標：\n{data['today_goal']}\n\n"
        message += f"【10:00~13:00】\n{data['time_10_13']}\n\n"
        message += f"【14:00~16:00】\n{data['time_14_16']}\n\n"
        message += f"【16:00~18:00】\n{data['time_16_18']}\n\n"
        message += f"【18:00~18:45】\n{data['time_18_1845']}\n"
        
        return message
    
    def format_noon_report(self, data):
        """昼の日報のフォーマット"""
        message = f"{data['date']} 中間報告\n\n"
        message += f"氏名：{data['name']}\n\n"
        message += f"■本社にいる間の目標\n{data['goal']}\n\n"
        message += f"■作業報告\n{data['work_report']}\n\n"
        message += f"■スケジュールに対しての進捗\n{data['progress']}\n\n"
        
        if data["progress"] == "遅れあり":
            message += f"■遅れている要因\n{data['delay_reason']}\n\n"
            message += f"■対策・改善案\n{data['delay_countermeasure']}\n"
        
        return message
    
    def format_evening_report(self, data):
        """夜の日報のフォーマット"""
        message = f"{data['date']} 最終報告\n\n"
        message += f"氏名：{data['name']}\n\n"
        message += f"■作業報告\n{data['work_report']}\n\n"
        message += f"■スケジュールに対しての進捗\n{data['progress']}\n\n"
        
        if data["progress"] == "遅れあり":
            message += f"■遅れている要因\n{data['delay_reason']}\n\n"
            message += f"■対策・改善案\n{data['delay_countermeasure']}\n"
        
        return message
    
    def send_lineworks_message(self, message):
        """LINE WORKS APIを使用してメッセージを送信"""
        api_key = self.config.get("api_key", "")
        channel_id = self.config.get("channel_id", "")
        
        if not api_key or not channel_id:
            messagebox.showerror("エラー", "LINE WORKS API設定が不完全です。設定画面で確認してください。")
            return False
        
        try:
            # LINE WORKS APIエンドポイント（実際のエンドポイントに置き換えてください）
            url = "https://apis.worksmobile.com/r/jp1xxx/message/v1/bot/message/push"
            
            # リクエストヘッダー
            headers = {
                "Content-Type": "application/json",
                "consumerKey": api_key
            }
            
            # リクエストボディ
            payload = {
                "botNo": channel_id,
                "channelNo": channel_id,
                "content": {
                    "type": "text",
                    "text": message
                }
            }
            
            # POSTリクエスト送信
            response = requests.post(url, headers=headers, json=payload)
            
            # レスポンス確認
            if response.status_code == 200:
                return True
            else:
                messagebox.showerror("送信エラー", f"エラーコード: {response.status_code}\n{response.text}")
                return False
                
        except Exception as e:
            messagebox.showerror("送信エラー", f"メッセージ送信中にエラーが発生しました: {str(e)}")
            return False#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LINEWORKSへの日報自動送信プログラム
日時指定で朝・昼・夜の日報をLINEWORKSへ自動送信し、履歴を管理するアプリケーション
"""

# 標準ライブラリ
import os
import json
import time
import sqlite3
import threading
import datetime
from tkinter import filedialog
import tkinter as tk
from tkinter import ttk, messagebox

# サードパーティライブラリ
import schedule
import requests
from tkcalendar import Calendar
from PIL import Image, ImageTk

# 設定ファイルのパス
CONFIG_FILE = "config.json"
# データベースファイルのパス
DATABASE_FILE = "reports.db"


class DailyReportApp:
    """LINE WORKSへ日報を自動送信し、履歴を管理するアプリケーション"""
    
    def __init__(self, root):
        """アプリケーションの初期化"""
        self.root = root
        self.root.title("日報自動送信システム")
        self.root.geometry("700x650")
        self.root.resizable(False, False)
        
        # 最初にスタイル設定
        self.setup_styles()
        
        # ユーザー設定を読み込み
        self.load_config()
        
        # データベース初期化
        self.setup_database()
        
        # メインフレーム
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 初回起動時は名前入力を促す
        if not self.config.get("name", "") or not self.config.get("api_key", ""):
            self.show_initial_setup()
        else:
            self.show_system_status()
        
        # スケジューラーを初期化
        self.setup_scheduler()
    
    def setup_styles(self):
        """スタイルの設定"""
        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 12))
        style.configure("TButton", font=("Helvetica", 12))
        style.configure("TEntry", font=("Helvetica", 12))
        style.configure("TText", font=("Helvetica", 12))
        style.configure("Header.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("Submit.TButton", font=("Helvetica", 14, "bold"))
        style.configure("Treeview", font=("Helvetica", 11))
        style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))
    
    def setup_database(self):
        """データベースの初期化"""
        # データベース接続
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # 日報テーブルの作成（存在しない場合）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            report_date TEXT NOT NULL,
            report_time TEXT NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 変更を保存
        conn.commit()
        conn.close()
    
    def load_config(self):
        """設定ファイルの読み込み"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self.config = {"name": "", "api_key": "", "channel_id": ""}
        else:
            self.config = {"name": "", "api_key": "", "channel_id": ""}
    
    def save_config(self):
        """設定の保存"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
    
    def show_initial_setup(self):
        """初期設定画面を表示"""
        # 既存のウィジェットをクリア
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # 初期設定ラベル
        ttk.Label(self.main_frame, text="初期設定", style="Header.TLabel").pack(pady=20)
        
        # 名前入力フレーム
        name_frame = ttk.Frame(self.main_frame)
        name_frame.pack(fill=tk.X, pady=10)
        ttk.Label(name_frame, text="氏名:").pack(side=tk.LEFT, padx=5)
        self.name_entry = ttk.Entry(name_frame, width=30)
        self.name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # LINE WORKS API キー入力フレーム
        api_frame = ttk.Frame(self.main_frame)
        api_frame.pack(fill=tk.X, pady=10)
        ttk.Label(api_frame, text="LINE WORKS API キー:").pack(side=tk.LEFT, padx=5)
        self.api_entry = ttk.Entry(api_frame, width=40)
        self.api_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # LINE WORKS チャンネルID入力フレーム
        channel_frame = ttk.Frame(self.main_frame)
        channel_frame.pack(fill=tk.X, pady=10)
        ttk.Label(channel_frame, text="LINE WORKS チャンネルID:").pack(side=tk.LEFT, padx=5)
        self.channel_entry = ttk.Entry(channel_frame, width=40)
        self.channel_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # LINE WORKS API についての説明
        info_frame = ttk.Frame(self.main_frame)
        info_frame.pack(fill=tk.X, pady=10)
        info_text = """LINE WORKS APIキーとチャンネルIDの取得方法:
1. LINE WORKS 管理者コンソールにログイン
2. 「ツール管理 > APIおよび開発 > サービスAPI」に移動
3. BOTを作成し、APIキーを取得
4. 使用するチャンネルIDを確認"""
        
        info_label = ttk.Label(info_frame, text=info_text, wraplength=500, justify="left")
        info_label.pack(pady=10)
        
        # 保存ボタン
        ttk.Button(self.main_frame, text="保存", command=self.save_initial_setup).pack(pady=20)
    
    def save_initial_setup(self):
        """初期設定を保存"""
        name = self.name_entry.get().strip()
        api_key = self.api_entry.get().strip()
        channel_id = self.channel_entry.get().strip()
        
        if not name:
            messagebox.showerror("エラー", "氏名を入力してください")
            return
        
        if not api_key:
            messagebox.showerror("エラー", "LINE WORKS API キーを入力してください")
            return
            
        if not channel_id:
            messagebox.showerror("エラー", "LINE WORKS チャンネルIDを入力してください")
            return
        
        self.config["name"] = name
        self.config["api_key"] = api_key
        self.config["channel_id"] = channel_id
        self.save_config()
        
        messagebox.showinfo("設定完了", "初期設定が完了しました")
        self.show_system_status()
    
    def show_system_status(self):
        """システム稼働状況画面を表示"""
        # 既存のウィジェットをクリア
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # システム状態ラベル
        ttk.Label(self.main_frame, text="日報自動送信システム", style="Header.TLabel").pack(pady=10)
        
        # ユーザー情報表示
        info_frame = ttk.Frame(self.main_frame)
        info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(info_frame, text=f"氏名: {self.config['name']}").pack(anchor=tk.W)
        
        # スケジュール表示
        schedule_frame = ttk.Frame(self.main_frame)
        schedule_frame.pack(fill=tk.X, pady=5)
        ttk.Label(schedule_frame, text="送信スケジュール:", style="TLabel").pack(anchor=tk.W)
        ttk.Label(schedule_frame, text="・朝の日報: 9:50").pack(anchor=tk.W, padx=20)
        ttk.Label(schedule_frame, text="・昼の日報: 12:50").pack(anchor=tk.W, padx=20)
        ttk.Label(schedule_frame, text="・夜の日報: 18:35").pack(anchor=tk.W, padx=20)
        
        # 次回送信予定
        now = datetime.datetime.now()
        next_time = self.get_next_report_time(now)
        next_time_str = next_time.strftime("%Y年%m月%d日 %H:%M")
        report_type = self.get_report_type(next_time)
        
        ttk.Label(self.main_frame, text=f"次回送信予定: {next_time_str} ({report_type}の日報)").pack(pady=5)
        
        # タブコントロール
        tab_control = ttk.Notebook(self.main_frame)
        tab_control.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 手動送信タブ
        manual_tab = ttk.Frame(tab_control)
        tab_control.add(manual_tab, text="手動送信")
        
        # 履歴タブ
        history_tab = ttk.Frame(tab_control)
        tab_control.add(history_tab, text="履歴参照")
        
        # 手動送信タブの内容
        ttk.Label(manual_tab, text="手動送信:", style="TLabel").pack(anchor=tk.W, pady=10)
        
        buttons_frame = ttk.Frame(manual_tab)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="朝の日報", command=lambda: self.show_report_form("morning")).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="昼の日報", command=lambda: self.show_report_form("noon")).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="夜の日報", command=lambda: self.show_report_form("evening")).pack(side=tk.LEFT, padx=10)
        
        # 履歴タブの内容
        self.setup_history_tab(history_tab)
        
        # 設定変更ボタン
        settings_frame = ttk.Frame(self.main_frame)
        settings_frame.pack(fill=tk.X, pady=10)
        ttk.Button(settings_frame, text="設定変更", command=self.show_settings).pack(side=tk.LEFT, padx=10)
    
    def setup_history_tab(self, parent_frame):
        """履歴参照タブの設定"""
        # 検索フレーム
        search_frame = ttk.Frame(parent_frame)
        search_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # 日付範囲選択
        ttk.Label(search_frame, text="期間:").pack(side=tk.LEFT, padx=5)
        
        # 開始日付
        self.start_date_var = tk.StringVar()
        today = datetime.datetime.now()
        one_month_ago = today - datetime.timedelta(days=30)
        self.start_date_var.set(one_month_ago.strftime("%Y-%m-%d"))
        start_date_entry = ttk.Entry(search_frame, textvariable=self.start_date_var, width=12)
        start_date_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="📅", width=2, 
                  command=lambda: self.show_calendar(self.start_date_var)).pack(side=tk.LEFT)
        
        ttk.Label(search_frame, text="〜").pack(side=tk.LEFT, padx=5)
        
        # 終了日付
        self.end_date_var = tk.StringVar()
        self.end_date_var.set(today.strftime("%Y-%m-%d"))
        end_date_entry = ttk.Entry(search_frame, textvariable=self.end_date_var, width=12)
        end_date_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="📅", width=2, 
                  command=lambda: self.show_calendar(self.end_date_var)).pack(side=tk.LEFT)
        
        # 日報タイプ選択
        ttk.Label(search_frame, text="種類:").pack(side=tk.LEFT, padx=10)
        self.report_type_var = tk.StringVar(value="全て")
        type_combo = ttk.Combobox(search_frame, textvariable=self.report_type_var, 
                                 values=["全て", "朝", "昼", "夜"], state="readonly", width=8)
        type_combo.pack(side=tk.LEFT, padx=5)
        
        # 検索ボタン
        ttk.Button(search_frame, text="検索", command=self.search_reports).pack(side=tk.LEFT, padx=20)
        
        # 履歴テーブル
        table_frame = ttk.Frame(parent_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ツリービューの列定義
        columns = ("日付", "時間", "種類", "氏名")
        self.report_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        
        # 列の見出しと幅の設定
        self.report_tree.heading("日付", text="日付")
        self.report_tree.heading("時間", text="時間")
        self.report_tree.heading("種類", text="種類")
        self.report_tree.heading("氏名", text="氏名")
        
        self.report_tree.column("日付", width=100)
        self.report_tree.column("時間", width=80)
        self.report_tree.column("種類", width=80)
        self.report_tree.column("氏名", width=100)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.report_tree.yview)
        self.report_tree.configure(yscroll=scrollbar.set)
        
        # 配置
        self.report_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 詳細表示ボタン
        detail_button = ttk.Button(parent_frame, text="詳細表示", command=self.show_report_detail)
        detail_button.pack(pady=10)
        
        # ダブルクリックイベント
        self.report_tree.bind("<Double-1>", lambda event: self.show_report_detail())
        
        # 初期データ読み込み
        self.search_reports()
    
    def show_calendar(self, date_var):
        """カレンダーダイアログを表示"""
        top = tk.Toplevel(self.root)
        top.title("日付選択")
        
        # 現在の日付を解析
        try:
            current_date = datetime.datetime.strptime(date_var.get(), "%Y-%m-%d").date()
        except:
            current_date = datetime.date.today()
        
        # カレンダーの作成
        cal = Calendar(top, selectmode="day", year=current_date.year, 
                     month=current_date.month, day=current_date.day,
                     locale='ja_JP', date_pattern='yyyy-mm-dd')
        cal.pack(pady=20)
        
        # 選択ボタン
        def set_date():
            date_var.set(cal.get_date())
            top.destroy()
        
        ttk.Button(top, text="選択", command=set_date).pack(pady=10)
    
    def search_reports(self):
        """日報履歴を検索して表示"""
        # 現在のツリービューをクリア
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        
        # 検索条件を取得
        try:
            start_date = self.start_date_var.get()
            end_date = self.end_date_var.get()
            report_type = self.report_type_var.get()
        except:
            # 変数がまだ定義されていない場合（初期表示時など）
            today = datetime.datetime.now()
            one_month_ago = today - datetime.timedelta(days=30)
            start_date = one_month_ago.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
            report_type = "全て"
        
        # データベース接続
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # クエリの作成
        query = "SELECT id, report_date, report_time, report_type, name FROM reports WHERE report_date BETWEEN ? AND ?"
        params = [start_date, end_date]
        
        # レポートタイプのフィルタリング
        if report_type != "全て":
            query += " AND report_type = ?"
            params.append(report_type)
        
        # 日付の降順で並べ替え
        query += " ORDER BY report_date DESC, report_time DESC"
        
        # クエリの実行
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # 結果をツリービューに追加
        for row in results:
            report_id, report_date, report_time, report_type, name = row
            self.report_tree.insert("", "end", iid=report_id, values=(report_date, report_time, report_type, name))
        
        conn.close()
    
    def show_report_detail(self):
        """選択された日報の詳細を表示"""
        # 選択されたアイテムを取得
        selected_id = self.report_tree.selection()
        if not selected_id:
            messagebox.showinfo("情報", "表示する日報を選択してください")
            return
        
        # 報告書IDを取得
        report_id = selected_id[0]
        
        # データベースから報告書データを取得
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        report_data = cursor.fetchone()
        conn.close()
        
        if not report_data:
            messagebox.showerror("エラー", "報告書データが見つかりませんでした")
            return
        
        # 報告書データを解析
        _, report_type, report_date, report_time, name, content, created_at = report_data
        
        # 詳細ウィンドウを作成
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"{report_date} {report_type}の日報")
        detail_window.geometry("600x500")
        
        # レポート詳細
        header_frame = ttk.Frame(detail_window, padding=10)
        header_frame.pack(fill=tk.X)
        
        ttk.Label(header_frame, text=f"{report_date} {report_type}の日報", style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"氏名: {name}").pack(anchor=tk.W, pady=5)
        ttk.Label(header_frame, text=f"時間: {report_time}").pack(anchor=tk.W, pady=2)
        
        # 内容表示
        content_frame = ttk.Frame(detail_window, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        content_text = tk.Text(content_frame, wrap=tk.WORD, height=20, width=70)
        content_text.insert("1.0", content)
        content_text.config(state=tk.DISABLED)  # 読み取り専用
        
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=content_text.yview)
        content_text.configure(yscrollcommand=scrollbar.set)
        
        content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 閉じるボタン
        ttk.Button(detail_window, text="閉じる", command=detail_window.destroy).pack(pady=10)
        
        # エクスポートボタン
        export_frame = ttk.Frame(detail_window)
        export_frame.pack(pady=5)
        ttk.Button(export_frame, text="テキストファイルに保存", 
                  command=lambda: self.export_report_to_file(report_data)).pack(side=tk.LEFT, padx=5)
    
    def export_report_to_file(self, report_data):
        """レポートをテキストファイルにエクスポート"""
        _, report_type, report_date, report_time, name, content, created_at = report_data
        
        # デフォルトのファイル名
        default_filename = f"{report_date}_{report_type}の日報_{name}.txt"
        
        # ファイル保存ダイアログ
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt")],
            initialfile=default_filename
        )
        
        if not file_path:
            return  # キャンセルされた場合
        
        # ファイルに書き込み
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"{report_date} {report_type}の日報\n\n")
                f.write(f"氏名: {name}\n")
                f.write(f"時間: {report_time}\n\n")
                f.write(content)
            
            messagebox.showinfo("保存完了", "レポートを保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイル保存中にエラーが発生しました: {str(e)}")
    
    def show_settings(self):
        """設定画面を表示"""
        # 既存のウィジェットをクリア
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # 設定ラベル
        ttk.Label(self.main_frame, text="設定変更", style="Header.TLabel").pack(pady=20)
        
        # 名前入力フレーム
        name_frame = ttk.Frame(self.main_frame)
        name_frame.pack(fill=tk.X, pady=10)
        ttk.Label(name_frame, text="氏名:").pack(side=tk.LEFT, padx=5)
        self.name_entry = ttk.Entry(name_frame, width=30)
        self.name_entry.insert(0, self.config.get("name", ""))
        self.name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # LINE WORKS API キー入力フレーム
        api_frame = ttk.Frame(self.main_frame)
        api_frame.pack(fill=tk.X, pady=10)
        ttk.Label(api_frame, text="LINE WORKS API キー:").pack(side=tk.LEFT, padx=5)
        self.api_entry = ttk.Entry(api_frame, width=40)
        self.api_entry.insert(0, self.config.get("api_key", ""))
        self.api_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # LINE WORKS チャンネルID入力フレーム
        channel_frame = ttk.Frame(self.main_frame)
        channel_frame.pack(fill=tk.X, pady=10)
        ttk.Label(channel_frame, text="LINE WORKS チャンネルID:").pack(side=tk.LEFT, padx=5)
        self.channel_entry = ttk.Entry(channel_frame, width=40)
        self.channel_entry.insert(0, self.config.get("channel_id", ""))
        self.channel_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="キャンセル", command=self.show_system_status).pack(side=tk.LEFT, padx=10)
    
    def save_settings(self):
        """設定変更を保存"""
        name = self.name_entry.get().strip()
        api_key = self.api_entry.get().strip()
        channel_id = self.channel_entry.get().strip()
        
        if not name:
            messagebox.showerror("エラー", "氏名を入力してください")
            return
        
        if not api_key:
            messagebox.showerror("エラー", "LINE WORKS API キーを入力してください")
            return
            
        if not channel_id:
            messagebox.showerror("エラー", "LINE WORKS チャンネルIDを入力してください")
            return
        
        self.config["name"] = name
        self.config["api_key"] = api_key
        self.config["channel_id"] = channel_id
        self.save_config()
        
        messagebox.showinfo("設定完了", "設定を更新しました")
        self.show_system_status()
    
    def show_report_form(self, report_type):
        """日報入力フォームを表示"""
        # 既存のウィジェットをクリア
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # 現在の日付を取得
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        today_display = datetime.datetime.now().strftime("%Y年%m月%d日")
        
        # フォームのタイトルとフィールドを設定
        if report_type == "morning":
            title = f"{today_display} スケジュール"
            type_name = "朝"
            fields = [
                {"name": "name", "label": "氏名", "type": "entry", "default": self.config.get("name", "")},
                {"name": "date", "label": "日付", "type": "entry", "default": today_display},
                {"name": "goal", "label": "■本社にいる間の目標", "type": "text"},
                {"name": "work_report", "label": "■作業報告", "type": "text"},
                {"name": "progress", "label": "■スケジュールに対しての進捗", "type": "dropdown", 
                 "options": ["順調", "遅れあり"], "default": "順調"}
            ]
        else:  # evening
            title = f"{today_display} 最終報告"
            type_name = "夜"
            fields = [
                {"name": "name", "label": "氏名", "type": "entry", "default": self.config.get("name", "")},
                {"name": "date", "label": "日付", "type": "entry", "default": today_display},
                {"name": "work_report", "label": "■作業報告", "type": "text"},
                {"name": "progress", "label": "■スケジュールに対しての進捗", "type": "dropdown", 
                 "options": ["順調", "遅れあり"], "default": "順調"}
            ]default": self.config.get("name", "")},
                {"name": "date", "label": "日付", "type": "entry", "default": today_display},
                {"name": "subject", "label": "勉強科目", "type": "entry"},
                {"name": "goal", "label": "取得目標", "type": "entry"},
                {"name": "today_goal", "label": "本日の目標", "type": "text"},
                {"name": "time_10_13", "label": "【10:00~13:00】", "type": "text"},
                {"name": "time_14_16", "label": "【14:00~16:00】", "type": "text"},
                {"name": "time_16_18", "label": "【16:00~18:00】", "type": "text"},
                {"name": "time_18_1845", "label": "【18:00~18:45】", "type": "text"}
            ]
        elif report_type == "noon":
            title = f"{today_display} 中間報告"
            type_name = "昼"
            fields = [
                {"name": "name", "label": "氏名", "type": "entry", "