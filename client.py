import tkinter as tk
from tkinter import messagebox, ttk
import requests

API_URL = "http://127.0.0.1:8000"
current_token = ""


def attempt_login():
    global current_token
    username = entry_username.get()
    password = entry_password.get()

    try:
        response = requests.post(
            f"{API_URL}/login",
            data={"username": username, "password": password}
        )

        if response.status_code == 200:
            current_token = response.json().get("access_token")
            messagebox.showinfo("Успех", "Вы успешно вошли в систему!")

            open_main_window()

        elif response.status_code == 401:
            messagebox.showerror("Ошибка доступа", "Неверный логин или пароль")
        else:
            messagebox.showerror("Ошибка",
                                 f"Неизвестная ошибка: {response.status_code}")

    except requests.exceptions.ConnectionError:
        messagebox.showerror("Ошибка сети",
                             "Не удалось подключиться к серверу.")


def open_main_window():
    root.withdraw()

    main_window = tk.Toplevel()
    main_window.title("Склад 1.0 - Панель управления")
    main_window.geometry("900x400")

    main_window.resizable(True, True)

    def load_items(search_query=""):
        for item in tree.get_children():
            tree.delete(item)

        headers = {"Authorization": f"Bearer {current_token}"}
        params = {"search": search_query} if search_query else {}

        try:
            response = requests.get(f"{API_URL}/items",
                                    headers=headers, params=params)

            if response.status_code == 200:
                items = response.json()

                for item in items:
                    tree.insert("", tk.END, values=(item["id"],
                                                    item["name"],
                                                    item["price"],
                                                    item["quantity"])
                                )

            else:
                messagebox.showerror(
                    "Ошибка",
                    f"Не удалось загрузить товары. Код: {response.status_code}"
                )

        except requests.exceptions.ConnectionError:
            messagebox.showerror("Ошибка сети", "Нет связи с сервером")

    def perform_search():
        query = entry_search.get()
        load_items(query)

    def update_quantity():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning(
                    "Внимание",
                    "Сначала выделите товар в таблице!"
            )
            return
        item_id = tree.item(selected[0])['values'][0]
        item_name = tree.item(selected[0])['values'][1]

        update_window = tk.Toplevel(main_window)
        update_window.title("Изменение остатка")
        update_window.geometry("300x150")
        update_window.resizable(False, False)

        tk.Label(update_window,
                 text=f"Товар: {item_name}",
                 font=("Arial", 10, "bold")).pack(pady=10)
        tk.Label(update_window,
                 text="На сколько изменить? (например, 5 или -3): ").pack()

        entry_amount = tk.Entry(update_window, width=15)
        entry_amount.pack(pady=5)

        def save_quantity():
            try:
                amount = int(entry_amount.get())

                headers = {"Authorization": f"Bearer {current_token}"}

                response = requests.put(
                    f"{API_URL}/items/{item_id}/quantity",
                    params={"amount_change": amount},
                    headers=headers
                )

                if response.status_code == 200:
                    update_window.destroy()
                    load_items()
                else:
                    messagebox.showerror(
                        "Ошибка",
                        f"Отказ сервера: {response.text}"
                    )

            except ValueError:
                messagebox.showerror(
                    "Ошибка ввода",
                    "Пожалуйста, введите целое число"
                )
            except requests.exceptions.ConnectionError:
                messagebox.showerror("Ошибка сети", "Нет связи с сервером")

        tk.Button(
            update_window,
            text="Сохранить",
            bg="lightgreen",
            command=save_quantity
        ).pack(pady=10)

    def add_new_item():
        add_window = tk.Toplevel(main_window)
        add_window.title("Новый товар")
        add_window.geometry("300x200")
        add_window.resizable(False, False)

        tk.Label(
            add_window,
            text="Наименование: ",
            font=("Arial", 10)
        ).pack(pady=(10, 0))
        entry_name = tk.Entry(add_window, width=30)
        entry_name.pack(pady=5)
        tk.Label(
            add_window,
            text="Цена: ",
            font=("Arial", 10)
        ).pack(pady=(10, 0))
        entry_price = tk.Entry(add_window, width=15)
        entry_price.pack(pady=5)

        def save_new_item():
            name = entry_name.get().strip()
            price_text = entry_price.get().strip().replace(',', '.')
            if not name:
                messagebox.showwarning(
                    "Внимание",
                    "Название товара не может быть пустым!"
                )
                return
            try:
                price = float(price_text)
                headers = {"Authorization": f"Bearer {current_token}"}
                new_item_data = {
                    "name": name,
                    "price": price
                }
                response = requests.post(
                    f"{API_URL}/items",
                    json=new_item_data,
                    headers=headers
                )

                if response.status_code == 200:
                    add_window.destroy()
                    load_items()
                else:
                    messagebox.showerror(
                        "Ошибка",
                        f"Отказ сервера: {response.text}"
                    )

            except ValueError:
                messagebox.showerror(
                    "Ошибка ввода",
                    "Введите корректную цену"
                )
            except requests.exceptions.ConnectionError:
                messagebox.showerror(
                    "Ошибка сети",
                    "Нет связи с сервером"
                )

        tk.Button(
            add_window,
            text="Добавить",
            bg="lightblue",
            command=save_new_item
        ).pack(pady=15)

    def delete_item():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning(
                "Внимание",
                "Сначала выделите товар для удаления!"
            )
            return
        item_id = tree.item(selected[0])['values'][0]
        item_name = tree.item(selected[0])['values'][1]

        confirm = messagebox.askyesno(
            "Подтверждение",
            f"Вы уверены,"
            "что хотите безвозвратно удалить товар?"
            f"'{item_name}'?"
        )

        if not confirm:
            return
        headers = {"Authorization": f"Bearer {current_token}"}
        try:
            response = requests.delete(
                f"{API_URL}/items/{item_id}",
                headers=headers
            )

            if response.status_code in (200, 204):
                load_items()
            else:
                messagebox.showerror(
                    "Ошикба",
                    f"Отказ сервера: {response.text}"
                )

        except requests.exceptions.ConnectionError:
            messagebox.showerror(
                "Ошибка сети",
                "Нет связи с сервером"
            )

    def sync_with_supplier():
        # TODO: API
        messagebox.showinfo(
            "Синхронизация",
            "Подключение к серверу поставщика"
        )

    top_frame = tk.Frame(main_window)
    top_frame.pack(fill=tk.X, padx=10, pady=5)

    tk.Label(
        top_frame,
        text="Поиск: "
    ).pack(side=tk.LEFT)

    entry_search = tk.Entry(top_frame, width=30)
    entry_search.pack(side=tk.LEFT, padx=5)
    btn_search = tk.Button(
        top_frame,
        text="Найти",
        width=10,
        command=perform_search
    )
    btn_search.pack(side=tk.LEFT)

    btn_update = tk.Button(
        top_frame,
        text="Изменить остаток",
        bg="lightgreen",
        command=update_quantity
    )
    btn_update.pack(side=tk.RIGHT, padx=5)

    btn_add = tk.Button(
        top_frame,
        text="Новый товар",
        bg="lightblue",
        command=add_new_item
    )
    btn_add.pack(side=tk.RIGHT)

    btn_sync = tk.Button(
        top_frame,
        text="Синхронизация",
        bg="lightyellow",
        command=sync_with_supplier
    )
    btn_sync.pack(side=tk.RIGHT, padx=5)

    btn_delete = tk.Button(
        top_frame,
        text="Удалить",
        width=10,
        bg="lightcoral",
        command=delete_item
    )
    btn_delete.pack(side=tk.RIGHT, padx=5)

    columns = (
        "id",
        "name",
        "price",
        "quantity"
    )

    tree = ttk.Treeview(
        main_window,
        columns=columns,
        show="headings"
    )

    tree.heading("id", text="ID")
    tree.heading("name", text="Наименование товара")
    tree.heading("price", text="Цена")
    tree.heading("quantity", text="Остаток на складе")

    tree.column(
        "id",
        width=50,
        anchor=tk.CENTER
    )
    tree.column(
        "name",
        width=300,
        anchor=tk.W
    )
    tree.column(
        "price",
        width=100,
        anchor=tk.CENTER
    )
    tree.column(
        "quantity",
        width=150,
        anchor=tk.CENTER
    )

    tree.pack(
        fill=tk.BOTH,
        expand=True,
        padx=10,
        pady=10
    )

    load_items()


root = tk.Tk()
root.title("Склад 1.0 - Вход")
root.geometry("300x250")
root.resizable(False, False)
tk.Label(
    root,
    text="Авторизация",
    font=("Arial", 14, "bold")
).pack(pady=15)

tk.Label(root, text="Логин: ").pack()
entry_username = tk.Entry(root, width=25)
entry_username.pack(pady=5)

tk.Label(root, text="Пароль: ").pack()
entry_password = tk.Entry(root, width=25, show="*")
entry_password.pack(pady=5)

tk.Button(
    root,
    text="Войти",
    command=attempt_login,
    width=15, bg="lightblue"
).pack(pady=20)

root.mainloop()
