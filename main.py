import flet as ft
from datetime import datetime
import random
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
import subprocess
import platform
import sys


# ════════════════════════════════════════════════════════
#  التحقق من نظام التشغيل
# ════════════════════════════════════════════════════════

def is_android():
    """التحقق مما إذا كان التطبيق يعمل على Android"""
    try:
        # التحقق من وجود خصائص Android
        if hasattr(sys, 'getandroidapilevel'):
            return True
        
        # التحقق من وجود مجلدات Android
        android_folders = ['/system/app', '/data/data', '/storage/emulated']
        for folder in android_folders:
            if os.path.exists(folder):
                return True
        
        # التحقق من متغيرات البيئة
        if os.environ.get('ANDROID_ROOT'):
            return True
            
    except:
        pass
    
    return False


def request_android_permissions(page: ft.Page):
    """طلب الصلاحيات المطلوبة للتطبيق على Android"""
    if not is_android():
        return
    
    permissions = [
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.BLUETOOTH_SCAN",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.READ_MEDIA_IMAGES",  # Android 13+
    ]
    
    for perm in permissions:
        try:
            if not page.has_permission(perm):
                page.request_permission(perm)
        except:
            pass


# ════════════════════════════════════════════════════════
#  دوال الطباعة الحرارية
# ════════════════════════════════════════════════════════

def reshape_arabic(text: str) -> str:
    """إعادة تشكيل النص العربي للعرض"""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        return text


def create_receipt_image(invoice_no: str, client: str, items: list, date: str) -> str:
    """إنشاء صورة للفاتورة وحفظها مؤقتاً"""
    # حساب المجاميع
    sub = sum(i["qty"] * i["price"] for i in items)
    tax = sub * 0.15
    total = sub + tax
    
    # إعدادات الصورة
    image_width = 576
    padding = 20
    content_width = image_width - (padding * 2)
    
    # إعداد الخطوط
    font_normal = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_large = ImageFont.load_default()
    font_bold = ImageFont.load_default()
    
    try:
        if platform.system() == 'Windows':
            font_path = "C:/Windows/Fonts/arial.ttf"
            if os.path.exists(font_path):
                font_normal = ImageFont.truetype(font_path, 14)
                font_small = ImageFont.truetype(font_path, 11)
                font_large = ImageFont.truetype(font_path, 18)
                font_bold = font_normal
        elif is_android():
            # مسارات الخطوط العربية على Android
            android_fonts = [
                "/system/fonts/DroidSansArabic.ttf",
                "/system/fonts/NotoSansArabic-Regular.ttf",
                "/system/fonts/Roboto-Regular.ttf"
            ]
            for font_path in android_fonts:
                if os.path.exists(font_path):
                    font_normal = ImageFont.truetype(font_path, 14)
                    font_small = ImageFont.truetype(font_path, 11)
                    font_large = ImageFont.truetype(font_path, 18)
                    font_bold = font_normal
                    break
    except Exception:
        pass
    
    # حساب ارتفاع الصورة
    line_height = 25
    total_lines = 12 + (len(items) * 2)
    image_height = total_lines * line_height + 100
    
    # إنشاء الصورة
    image = Image.new('RGB', (image_width, image_height), color='white')
    draw = ImageDraw.Draw(image)
    y_offset = padding
    
    def draw_line(y):
        draw.line([(padding, y), (image_width-padding, y)], fill='black', width=1)
    
    def draw_double_line(y):
        draw.line([(padding, y), (image_width-padding, y)], fill='black', width=2)
        draw.line([(padding, y+3), (image_width-padding, y+3)], fill='black', width=2)
    
    # العنوان
    title = "فاتورة ضريبية"
    title_reshaped = reshape_arabic(title)
    bbox = draw.textbbox((0, 0), title_reshaped, font=font_large)
    text_width = bbox[2] - bbox[0]
    draw.text(((image_width - text_width) // 2, y_offset), title_reshaped, fill='black', font=font_large)
    y_offset += 30
    
    # اسم الشركة
    company = "غانم سوفت"
    company_reshaped = reshape_arabic(company)
    bbox = draw.textbbox((0, 0), company_reshaped, font=font_normal)
    text_width = bbox[2] - bbox[0]
    draw.text(((image_width - text_width) // 2, y_offset), company_reshaped, fill='black', font=font_normal)
    y_offset += 25
    
    draw_double_line(y_offset)
    y_offset += 15
    
    # معلومات الفاتورة
    draw.text((padding, y_offset), reshape_arabic(f"رقم الفاتورة: {invoice_no}"), fill='black', font=font_normal)
    y_offset += line_height
    draw.text((padding, y_offset), reshape_arabic(f"التاريخ: {date}"), fill='black', font=font_normal)
    y_offset += line_height
    draw.text((padding, y_offset), reshape_arabic(f"العميل: {client or 'عميل عام'}"), fill='black', font=font_normal)
    y_offset += line_height
    
    draw_line(y_offset)
    y_offset += 15
    
    # رأس الجدول
    draw.text((padding + content_width - 100, y_offset), reshape_arabic("الإجمالي"), fill='black', font=font_bold)
    draw.text((padding + 200, y_offset), reshape_arabic("الكمية × السعر"), fill='black', font=font_bold)
    draw.text((padding, y_offset), reshape_arabic("المنتج"), fill='black', font=font_bold)
    y_offset += line_height
    
    draw_line(y_offset)
    y_offset += 10
    
    # عناصر الفاتورة
    for item in items:
        item_name = item["name"][:30]
        item_total = item['qty'] * item['price']
        
        draw.text((padding, y_offset), reshape_arabic(item_name), fill='black', font=font_normal)
        y_offset += 18
        draw.text((padding + 200, y_offset), reshape_arabic(f"{item['qty']} × {item['price']:.2f}"), 
                 fill='black', font=font_small)
        draw.text((image_width - padding - 80, y_offset), f"{item_total:.2f}", fill='black', font=font_normal)
        y_offset += line_height
    
    draw_line(y_offset)
    y_offset += 15
    
    # الملخص
    draw.text((image_width - padding - 200, y_offset), reshape_arabic(f"المجموع الجزئي: {sub:,.2f} ر.س"), 
             fill='black', font=font_normal)
    y_offset += line_height
    draw.text((image_width - padding - 200, y_offset), reshape_arabic(f"ضريبة 15%: {tax:,.2f} ر.س"), 
             fill='black', font=font_normal)
    y_offset += line_height
    
    draw_double_line(y_offset)
    y_offset += 15
    
    draw.text((image_width - padding - 200, y_offset), reshape_arabic(f"الإجمالي: {total:,.2f} ر.س"), 
             fill='black', font=font_bold)
    y_offset += 30
    
    # تذييل
    thanks = "شكراً لتعاملكم معنا!"
    thanks_reshaped = reshape_arabic(thanks)
    bbox = draw.textbbox((0, 0), thanks_reshaped, font=font_normal)
    text_width = bbox[2] - bbox[0]
    draw.text(((image_width - text_width) // 2, y_offset), thanks_reshaped, fill='black', font=font_normal)
    y_offset += 25
    
    company_footer = "غانم سوفت"
    company_reshaped = reshape_arabic(company_footer)
    bbox = draw.textbbox((0, 0), company_reshaped, font=font_normal)
    text_width = bbox[2] - bbox[0]
    draw.text(((image_width - text_width) // 2, y_offset), company_reshaped, fill='black', font=font_normal)
    
    # حفظ الصورة
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    image.save(temp_file.name, 'PNG')
    temp_file.close()
    
    return temp_file.name


def open_with_esc_pos_printer(image_path: str) -> bool:
    """فتح الصورة مع تطبيق ESC POS Printer"""
    try:
        if is_android():
            # على Android
            intent_cmd = [
                'am', 'start', '-a', 'android.intent.action.VIEW',
                '-d', f'file://{image_path}',
                '-t', 'image/png'
            ]
            subprocess.run(intent_cmd, capture_output=True)
            return True
        elif platform.system() == 'Windows':
            os.startfile(image_path)
            return True
        elif platform.system() == 'Darwin':
            subprocess.run(['open', image_path])
            return True
        else:
            subprocess.run(['xdg-open', image_path])
            return True
    except Exception:
        return False


# ════════════════════════════════════════════════════════
#  واجهة Flet
# ════════════════════════════════════════════════════════

def main(page: ft.Page):
    # طلب الصلاحيات على Android
    if is_android():
        request_android_permissions(page)
    
    page.title = "نظام الفواتير"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F0F4F8"
    page.padding = 0
    page.fonts = {
        "Cairo": "https://fonts.gstatic.com/s/cairo/v28/SLXgc1nY6HkvalIvTp0iZg.woff2"
    }
    page.theme = ft.Theme(font_family="Cairo")

    invoice_items = []
    invoice_counter = [random.randint(1000, 9999)]
    current_image_path = [None]

    def calc_totals():
        sub = sum(i["qty"] * i["price"] for i in invoice_items)
        tax = sub * 0.15
        return sub, tax, sub + tax

    def show_snack(msg: str, color: str = "#10B981"):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, text_align=ft.TextAlign.CENTER, color="#FFFFFF"),
            bgcolor=color,
        )
        page.snack_bar.open = True
        page.update()

    def refresh_table():
        rows = []
        for idx, item in enumerate(invoice_items):
            total = item["qty"] * item["price"]
            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(idx + 1), text_align=ft.TextAlign.CENTER)),
                    ft.DataCell(ft.Text(item["name"])),
                    ft.DataCell(ft.Text(str(item["qty"]), text_align=ft.TextAlign.CENTER)),
                    ft.DataCell(ft.Text(f'{item["price"]:,.2f}', text_align=ft.TextAlign.CENTER)),
                    ft.DataCell(ft.Text(f'{total:,.2f}', text_align=ft.TextAlign.CENTER,
                                        weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color="#EF4444",
                        tooltip="حذف",
                        on_click=lambda e, i=idx: delete_item(i),
                    )),
                ])
            )
        items_table.rows = rows
        sub, tax, total = calc_totals()
        subtotal_text.value = f"{sub:,.2f} ر.س"
        tax_text.value = f"{tax:,.2f} ر.س"
        total_text.value = f"{total:,.2f} ر.س"
        page.update()

    def delete_item(idx):
        invoice_items.pop(idx)
        refresh_table()

    def add_item(e):
        name = field_name.value.strip()
        qty_str = field_qty.value.strip()
        price_str = field_price.value.strip()
        error = False

        if not name:
            field_name.error_text = "أدخل اسم المنتج"
            error = True
        else:
            field_name.error_text = None

        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
            field_qty.error_text = None
        except ValueError:
            field_qty.error_text = "كمية غير صحيحة"
            error = True

        try:
            price = float(price_str)
            if price < 0:
                raise ValueError
            field_price.error_text = None
        except ValueError:
            field_price.error_text = "سعر غير صحيح"
            error = True

        if error:
            page.update()
            return

        invoice_items.append({"name": name, "qty": qty, "price": price})
        field_name.value = field_qty.value = field_price.value = ""
        field_name.focus()
        refresh_table()

    def clear_invoice(e):
        invoice_items.clear()
        invoice_counter[0] = random.randint(1000, 9999)
        invoice_number.value = f"#{invoice_counter[0]}"
        refresh_table()
        if current_image_path[0] and os.path.exists(current_image_path[0]):
            try:
                os.unlink(current_image_path[0])
            except:
                pass
            current_image_path[0] = None

    def do_print(e):
        if not invoice_items:
            show_snack("لا توجد منتجات في الفاتورة!", "#EF4444")
            return

        try:
            image_path = create_receipt_image(
                invoice_no=str(invoice_counter[0]),
                client=field_client.value,
                items=invoice_items,
                date=datetime.now().strftime("%Y-%m-%d"),
            )
            current_image_path[0] = image_path
            
            if open_with_esc_pos_printer(image_path):
                show_snack("✅ تم فتح الصورة في تطبيق الطابعة", "#10B981")
            else:
                preview_image.src = image_path
                preview_dialog.open = True
                page.update()
                
        except Exception as ex:
            show_snack(f"حدث خطأ: {str(ex)}", "#EF4444")

    # واجهة المستخدم
    preview_image = ft.Image(width=400, height=420, src="")
    preview_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("معاينة الفاتورة", weight=ft.FontWeight.BOLD,
                      text_align=ft.TextAlign.CENTER),
        content=ft.Container(
            content=ft.Column([preview_image], scroll=ft.ScrollMode.AUTO),
            width=450, height=500,
            bgcolor="#F8FAFC", border_radius=8, padding=16,
        ),
        actions=[
            ft.TextButton(
                "طباعة",
                on_click=lambda e: open_with_esc_pos_printer(current_image_path[0]) or 
                                   (setattr(preview_dialog, "open", False) or page.update()),
            ),
            ft.TextButton(
                "إغلاق",
                on_click=lambda e: setattr(preview_dialog, "open", False) or page.update(),
            )
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.overlay.append(preview_dialog)

    # باقي عناصر الواجهة...
    invoice_number = ft.Text(f"#{invoice_counter[0]}", size=14, color="#64748B", weight=ft.FontWeight.W_500)

    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.RECEIPT_LONG, color="#3B82F6", size=28),
                ft.Text("نظام الفواتير", size=22, weight=ft.FontWeight.BOLD, color="#1E293B"),
            ], spacing=10),
            ft.Column([
                ft.Text("رقم الفاتورة", size=11, color="#94A3B8"),
                invoice_number,
            ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor="#FFFFFF",
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
    )

    field_client = ft.TextField(
        label="اسم العميل",
        hint_text="أدخل اسم العميل...",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border_radius=10,
        filled=True,
        fill_color="#FFFFFF",
        expand=True,
    )

    client_card = ft.Container(
        content=ft.Column([
            ft.Text("بيانات العميل", size=14, weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Row([
                field_client,
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color="#64748B"),
                        ft.Text(datetime.now().strftime("%Y/%m/%d"), size=14, color="#475569"),
                    ], spacing=6),
                    bgcolor="#F1F5F9",
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=18),
                ),
            ], spacing=12),
        ], spacing=12),
        bgcolor="#FFFFFF",
        border_radius=14,
        padding=20,
    )

    field_name = ft.TextField(
        label="اسم المنتج",
        hint_text="مثال: استشارة",
        border_radius=10,
        filled=True,
        fill_color="#FFFFFF",
        expand=2,
        on_submit=add_item,
    )
    field_qty = ft.TextField(
        label="الكمية",
        hint_text="1",
        border_radius=10,
        filled=True,
        fill_color="#FFFFFF",
        expand=1,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_submit=add_item,
    )
    field_price = ft.TextField(
        label="السعر (ر.س)",
        hint_text="0.00",
        border_radius=10,
        filled=True,
        fill_color="#FFFFFF",
        expand=1,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_submit=add_item,
    )

    add_card = ft.Container(
        content=ft.Column([
            ft.Text("إضافة منتج", size=14, weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Row([field_name, field_qty, field_price], spacing=12),
            ft.ElevatedButton(
                "إضافة للفاتورة",
                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                on_click=add_item,
                style=ft.ButtonStyle(
                    bgcolor="#3B82F6",
                    color="#FFFFFF",
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
            ),
        ], spacing=14),
        bgcolor="#FFFFFF",
        border_radius=14,
        padding=20,
    )

    items_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("#", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("المنتج", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("الكمية", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("السعر", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("الإجمالي", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("", text_align=ft.TextAlign.CENTER)),
        ],
        rows=[],
        border=ft.border.all(1, "#E2E8F0"),
        border_radius=10,
        heading_row_color="#F8FAFC",
        expand=True,
    )

    table_card = ft.Container(
        content=ft.Column([
            ft.Text("المنتجات", size=14, weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Container(content=ft.Row([items_table], scroll=ft.ScrollMode.AUTO), border_radius=10),
        ], spacing=14),
        bgcolor="#FFFFFF",
        border_radius=14,
        padding=20,
    )

    subtotal_text = ft.Text("0.00 ر.س", size=15, color="#475569")
    tax_text = ft.Text("0.00 ر.س", size=15, color="#F59E0B")
    total_text = ft.Text("0.00 ر.س", size=20, color="#3B82F6", weight=ft.FontWeight.BOLD)

    totals_card = ft.Container(
        content=ft.Column([
            ft.Text("ملخص الفاتورة", size=14, weight=ft.FontWeight.BOLD, color="#1E293B"),
            ft.Divider(),
            ft.Row([ft.Text("المجموع الجزئي"), subtotal_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("ضريبة 15%"), tax_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Row([ft.Text("الإجمالي", weight=ft.FontWeight.BOLD), total_text], 
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=14),
        bgcolor="#FFFFFF",
        border_radius=14,
        padding=20,
    )

    actions_row = ft.Row([
        ft.OutlinedButton("فاتورة جديدة", icon=ft.Icons.ADD, on_click=clear_invoice),
        ft.ElevatedButton("طباعة 🖨️", icon=ft.Icons.PRINT, on_click=do_print,
                         style=ft.ButtonStyle(bgcolor="#10B981", color="#FFFFFF")),
    ], alignment=ft.MainAxisAlignment.END, spacing=12)

    print_note = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, color="#3B82F6", size=16),
            ft.Text("اضغط طباعة لفتح الفاتورة في تطبيق الطابعة", size=12, color="#64748B"),
        ], spacing=8),
        bgcolor="#EFF6FF",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )

    content = ft.Column([
        client_card,
        add_card,
        table_card,
        totals_card,
        print_note,
        actions_row,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    page.add(ft.Column([
        header,
        ft.Container(content=content, padding=ft.padding.all(20), expand=True),
    ], spacing=0, expand=True))


if __name__ == "__main__":
    ft.app(target=main)