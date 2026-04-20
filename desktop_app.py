"""
AURASUTRA - Desktop WhatsApp Sender
A pure Python desktop application for personalized WhatsApp outreach.
Run locally - NOT for cloud deployment.
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd

from utils import validate_dataframe, substitute_template, COUNTRY_CODES
from whatsapp_sender import WhatsAppSender

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(data: dict):
    existing = load_config()
    existing.update(data)
    with open(CONFIG_FILE, "w") as f:
        json.dump(existing, f)


class AurasutraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AURASUTRA - WhatsApp Outreach")
        self.root.geometry("900x750")
        self.root.configure(bg="#1a0a2e")
        
        # State
        self.df = None
        self.sending = False
        self.sender = None
        
        # Load config
        self.config = load_config()
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        # Build UI
        self.create_widgets()
        
    def configure_styles(self):
        # Main frame style
        self.style.configure("Main.TFrame", background="#1a0a2e")
        self.style.configure("Card.TFrame", background="#2d1b4e")
        
        # Labels
        self.style.configure("Title.TLabel", 
                           background="#1a0a2e", 
                           foreground="#C9A84C",
                           font=("Segoe UI", 24, "bold"))
        self.style.configure("Subtitle.TLabel",
                           background="#1a0a2e",
                           foreground="#b89cdd",
                           font=("Segoe UI", 10))
        self.style.configure("Section.TLabel",
                           background="#1a0a2e",
                           foreground="#C9A84C",
                           font=("Segoe UI", 9, "bold"))
        self.style.configure("Info.TLabel",
                           background="#1a0a2e",
                           foreground="#F0E6FF",
                           font=("Segoe UI", 9))
        
        # Buttons
        self.style.configure("Gold.TButton",
                           background="#C9A84C",
                           foreground="#1a0a2e",
                           font=("Segoe UI", 10, "bold"),
                           padding=(15, 8))
        self.style.map("Gold.TButton",
                      background=[('active', '#f0d080'), ('pressed', '#a88a3c')])
        
        self.style.configure("Send.TButton",
                           background="#4CAF50",
                           foreground="white",
                           font=("Segoe UI", 12, "bold"),
                           padding=(20, 12))
        
        # Entry and Combobox
        self.style.configure("TCombobox", padding=5)
        self.style.configure("TSpinbox", padding=5)
        
    def create_widgets(self):
        # Main container with scrollbar
        main_canvas = tk.Canvas(self.root, bg="#1a0a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        self.main_frame = ttk.Frame(main_canvas, style="Main.TFrame")
        
        self.main_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        main_canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)
        
        # Bind mousewheel
        def on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Header
        self.create_header()
        
        # Sections
        self.create_config_section()
        self.create_contacts_section()
        self.create_template_section()
        self.create_preview_section()
        self.create_send_section()
        self.create_log_section()
        
    def create_header(self):
        header_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title = ttk.Label(header_frame, text="✦ AURASUTRA ✦", style="Title.TLabel")
        title.pack()
        
        subtitle = ttk.Label(header_frame, 
                           text="Personalized WhatsApp Outreach • Cold Messaging, Automated",
                           style="Subtitle.TLabel")
        subtitle.pack()
        
        # Separator
        sep = tk.Frame(self.main_frame, height=1, bg="#C9A84C")
        sep.pack(fill="x", padx=20, pady=15)
        
    def create_config_section(self):
        section = ttk.Frame(self.main_frame, style="Main.TFrame")
        section.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(section, text="01 — CONFIGURATION", style="Section.TLabel").pack(anchor="w")
        
        config_frame = ttk.Frame(section, style="Main.TFrame")
        config_frame.pack(fill="x", pady=10)
        
        # Country code
        cc_frame = ttk.Frame(config_frame, style="Main.TFrame")
        cc_frame.pack(side="left", padx=(0, 20))
        
        ttk.Label(cc_frame, text="Default Country Code:", style="Info.TLabel").pack(anchor="w")
        self.country_var = tk.StringVar(value=self.config.get("country_label", list(COUNTRY_CODES.keys())[0]))
        country_combo = ttk.Combobox(cc_frame, textvariable=self.country_var, 
                                    values=list(COUNTRY_CODES.keys()), width=25, state="readonly")
        country_combo.pack(pady=5)
        country_combo.bind("<<ComboboxSelected>>", self.on_config_change)
        
        # Wait time
        wait_frame = ttk.Frame(config_frame, style="Main.TFrame")
        wait_frame.pack(side="left", padx=20)
        
        ttk.Label(wait_frame, text="Wait time per message (sec):", style="Info.TLabel").pack(anchor="w")
        self.wait_var = tk.IntVar(value=self.config.get("wait_time", 30))
        wait_spin = ttk.Spinbox(wait_frame, from_=10, to=60, textvariable=self.wait_var, width=10)
        wait_spin.pack(pady=5)
        
        # Delay between messages
        delay_frame = ttk.Frame(config_frame, style="Main.TFrame")
        delay_frame.pack(side="left", padx=20)
        
        ttk.Label(delay_frame, text="Delay between messages (sec):", style="Info.TLabel").pack(anchor="w")
        self.delay_var = tk.IntVar(value=self.config.get("inter_delay", 5))
        delay_spin = ttk.Spinbox(delay_frame, from_=2, to=60, textvariable=self.delay_var, width=10)
        delay_spin.pack(pady=5)
        
    def create_contacts_section(self):
        section = ttk.Frame(self.main_frame, style="Main.TFrame")
        section.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(section, text="02 — CONTACTS", style="Section.TLabel").pack(anchor="w")
        
        btn_frame = ttk.Frame(section, style="Main.TFrame")
        btn_frame.pack(fill="x", pady=10)
        
        upload_btn = ttk.Button(btn_frame, text="📂 Upload Contacts (CSV/Excel)", 
                               command=self.upload_contacts, style="Gold.TButton")
        upload_btn.pack(side="left")
        
        sample_btn = ttk.Button(btn_frame, text="📥 Download Sample", 
                               command=self.download_sample, style="Gold.TButton")
        sample_btn.pack(side="left", padx=10)
        
        # Status label
        self.contacts_status = ttk.Label(section, text="No file uploaded", style="Info.TLabel")
        self.contacts_status.pack(anchor="w", pady=5)
        
        # Contacts preview (treeview)
        self.contacts_tree = ttk.Treeview(section, columns=("mobile", "name", "clinic_name", "location"),
                                         show="headings", height=5)
        self.contacts_tree.heading("mobile", text="Mobile")
        self.contacts_tree.heading("name", text="Name")
        self.contacts_tree.heading("clinic_name", text="Clinic Name")
        self.contacts_tree.heading("location", text="Location")
        
        for col in ("mobile", "name", "clinic_name", "location"):
            self.contacts_tree.column(col, width=150)
            
        self.contacts_tree.pack(fill="x", pady=5)
        
    def create_template_section(self):
        section = ttk.Frame(self.main_frame, style="Main.TFrame")
        section.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(section, text="03 — MESSAGE TEMPLATE", style="Section.TLabel").pack(anchor="w")
        ttk.Label(section, text="Placeholders: {name} {clinic_name} {location} — any column from your file works",
                 style="Info.TLabel").pack(anchor="w", pady=(0, 5))
        
        default_template = (
            "Hi {name},\n\n"
            "I came across {clinic_name} in {location} and wanted to reach out personally.\n\n"
            "We help clinics like yours grow their patient base through smart digital outreach. "
            "Would love to connect and explore if there's a fit.\n\n"
            "— Aurasutra Team"
        )
        
        self.template_text = scrolledtext.ScrolledText(section, height=8, width=80,
                                                       bg="#2d1b4e", fg="#F0E6FF",
                                                       insertbackground="#C9A84C",
                                                       font=("Consolas", 10))
        self.template_text.insert("1.0", default_template)
        self.template_text.pack(fill="x", pady=5)
        
    def create_preview_section(self):
        section = ttk.Frame(self.main_frame, style="Main.TFrame")
        section.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(section, text="04 — PREVIEW", style="Section.TLabel").pack(anchor="w")
        
        preview_btn = ttk.Button(section, text="👁 Preview for First Contact", 
                                command=self.preview_message, style="Gold.TButton")
        preview_btn.pack(anchor="w", pady=5)
        
        self.preview_text = scrolledtext.ScrolledText(section, height=6, width=80,
                                                      bg="#2d1b4e", fg="#F0E6FF",
                                                      font=("Consolas", 10), state="disabled")
        self.preview_text.pack(fill="x", pady=5)
        
    def create_send_section(self):
        section = ttk.Frame(self.main_frame, style="Main.TFrame")
        section.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(section, text="05 — SEND", style="Section.TLabel").pack(anchor="w")
        
        # Info box
        info_text = (
            "⚠️ IMPORTANT:\n"
            "1. WhatsApp Web will open in Chrome\n"
            "2. If not logged in, scan the QR code with your WhatsApp mobile app\n"
            "3. Keep Chrome window visible - don't minimize it\n"
            "4. Messages will send automatically after login"
        )
        
        info_label = tk.Label(section, text=info_text, bg="#3d2b5e", fg="#F0E6FF",
                             justify="left", padx=15, pady=10, font=("Segoe UI", 9))
        info_label.pack(fill="x", pady=10)
        
        # Progress
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(section, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(pady=10)
        
        self.progress_label = ttk.Label(section, text="Ready to send", style="Info.TLabel")
        self.progress_label.pack()
        
        # Send button
        self.send_btn = tk.Button(section, text="🚀 SEND TO ALL CONTACTS",
                                 bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"),
                                 padx=30, pady=12, command=self.start_sending,
                                 activebackground="#45a049")
        self.send_btn.pack(pady=15)
        
        # Stop button (hidden initially)
        self.stop_btn = tk.Button(section, text="⏹ STOP SENDING",
                                 bg="#f44336", fg="white", font=("Segoe UI", 10, "bold"),
                                 padx=20, pady=8, command=self.stop_sending,
                                 activebackground="#d32f2f")
        
    def create_log_section(self):
        section = ttk.Frame(self.main_frame, style="Main.TFrame")
        section.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(section, text="06 — SEND LOG", style="Section.TLabel").pack(anchor="w")
        
        # Results treeview
        self.results_tree = ttk.Treeview(section, columns=("contact", "number", "status", "error"),
                                        show="headings", height=8)
        self.results_tree.heading("contact", text="Contact")
        self.results_tree.heading("number", text="Number")
        self.results_tree.heading("status", text="Status")
        self.results_tree.heading("error", text="Error")
        
        self.results_tree.column("contact", width=150)
        self.results_tree.column("number", width=150)
        self.results_tree.column("status", width=80)
        self.results_tree.column("error", width=300)
        
        self.results_tree.pack(fill="x", pady=5)
        
        # Export button
        export_btn = ttk.Button(section, text="📄 Export Results to CSV",
                               command=self.export_results, style="Gold.TButton")
        export_btn.pack(anchor="w", pady=10)
        
        # Summary
        self.summary_label = ttk.Label(section, text="", style="Info.TLabel")
        self.summary_label.pack(anchor="w")
        
    def on_config_change(self, event=None):
        save_config({
            "country_label": self.country_var.get(),
            "wait_time": self.wait_var.get(),
            "inter_delay": self.delay_var.get()
        })
        
    def upload_contacts(self):
        filetypes = [
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*")
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        
        if not filepath:
            return
            
        try:
            if filepath.endswith(".csv"):
                df = pd.read_csv(filepath, skipinitialspace=True)
            else:
                df = pd.read_excel(filepath, engine="openpyxl")
                
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            for col in df.select_dtypes(include=["object", "str"]).columns:
                df[col] = df[col].astype(str).str.strip()
                
            is_valid, errors = validate_dataframe(df)
            if not is_valid:
                messagebox.showerror("Validation Error", "\n".join(errors))
                return
                
            self.df = df
            self.contacts_status.config(text=f"✅ Loaded {len(df)} contacts from {os.path.basename(filepath)}")
            
            # Clear and populate treeview
            for item in self.contacts_tree.get_children():
                self.contacts_tree.delete(item)
                
            for _, row in df.head(5).iterrows():
                self.contacts_tree.insert("", "end", values=(
                    row.get("mobile", ""),
                    row.get("name", ""),
                    row.get("clinic_name", ""),
                    row.get("location", "")
                ))
                
            if len(df) > 5:
                self.contacts_tree.insert("", "end", values=(f"... and {len(df)-5} more", "", "", ""))
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")
            
    def download_sample(self):
        sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_contacts.csv")
        if os.path.exists(sample_path):
            save_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile="sample_contacts.csv"
            )
            if save_path:
                import shutil
                shutil.copy(sample_path, save_path)
                messagebox.showinfo("Success", f"Sample saved to {save_path}")
        else:
            messagebox.showerror("Error", "Sample file not found")
            
    def preview_message(self):
        if self.df is None or len(self.df) == 0:
            messagebox.showwarning("Warning", "Upload contacts first")
            return
            
        template = self.template_text.get("1.0", "end-1c")
        rendered = substitute_template(template, self.df.iloc[0].to_dict())
        
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", rendered)
        self.preview_text.config(state="disabled")
        
    def start_sending(self):
        if self.df is None or len(self.df) == 0:
            messagebox.showwarning("Warning", "Upload contacts first")
            return
            
        template = self.template_text.get("1.0", "end-1c").strip()
        if not template:
            messagebox.showwarning("Warning", "Enter a message template")
            return
            
        if not messagebox.askyesno("Confirm", f"Send messages to {len(self.df)} contacts?"):
            return
            
        self.sending = True
        self.send_btn.config(state="disabled")
        self.stop_btn.pack(pady=5)
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        self.all_results = []
        
        # Start sending in a thread
        thread = threading.Thread(target=self.send_messages, args=(template,), daemon=True)
        thread.start()
        
    def send_messages(self, template):
        default_cc = COUNTRY_CODES[self.country_var.get()]
        
        self.sender = WhatsAppSender(
            wait_time=self.wait_var.get(),
            inter_message_delay=self.delay_var.get(),
            default_cc=default_cc,
            qr_timeout=180
        )
        
        total = len(self.df)
        
        def on_progress(done, total_count, result):
            self.all_results.append(result)
            progress = (done / total_count) * 100
            
            # Update UI from main thread
            self.root.after(0, lambda: self.update_progress(done, total_count, result, progress))
            
        def on_status(msg):
            self.root.after(0, lambda: self.progress_label.config(text=msg))
            
        try:
            self.sender.send_batch(
                self.df, template,
                progress_callback=on_progress,
                status_cb=on_status
            )
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, self.sending_complete)
            
    def update_progress(self, done, total, result, progress):
        self.progress_var.set(progress)
        
        icon = "✅" if result["status"] == "sent" else "❌"
        self.progress_label.config(text=f"{icon} {done}/{total} — {result['contact']} ({result['number']})")
        
        # Add to results tree
        self.results_tree.insert("", "end", values=(
            result["contact"],
            result["number"],
            result["status"],
            result.get("error", "")
        ))
        
        # Auto-scroll to bottom
        self.results_tree.yview_moveto(1)
        
    def sending_complete(self):
        self.sending = False
        self.send_btn.config(state="normal")
        self.stop_btn.pack_forget()
        
        if self.all_results:
            sent = sum(1 for r in self.all_results if r["status"] == "sent")
            failed = sum(1 for r in self.all_results if r["status"] == "failed")
            self.summary_label.config(text=f"✅ Sent: {sent}  |  ❌ Failed: {failed}  |  Total: {len(self.all_results)}")
            
        self.progress_label.config(text="Sending complete!")
        messagebox.showinfo("Complete", "Message sending completed!")
        
    def stop_sending(self):
        self.sending = False
        if self.sender:
            self.sender.close()
        self.progress_label.config(text="Sending stopped by user")
        self.send_btn.config(state="normal")
        self.stop_btn.pack_forget()
        
    def export_results(self):
        if not self.all_results:
            messagebox.showwarning("Warning", "No results to export")
            return
            
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="aurasutra_report.csv"
        )
        
        if save_path:
            results_df = pd.DataFrame(self.all_results)
            results_df.to_csv(save_path, index=False)
            messagebox.showinfo("Success", f"Results saved to {save_path}")


def main():
    root = tk.Tk()
    app = AurasutraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
