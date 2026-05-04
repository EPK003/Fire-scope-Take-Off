
import streamlit as st
import pandas as pd
import fitz
from PIL import Image, ImageDraw
import io
from datetime import datetime
from streamlit_drawable_canvas import st_canvas

# ------------------------------------------------------------
# FIRE SCOPE TAKEOFF PORTAL V1
# Private online-ready Streamlit app
# ------------------------------------------------------------

st.set_page_config(
    page_title="FireScope Takeoff Portal",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Simple private login
# -----------------------------
def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

APP_PASSWORD = get_secret("APP_PASSWORD", "change-this-password")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_screen():
    st.markdown("""
    <style>
    .login-box {
        max-width: 520px;
        margin: 8vh auto;
        padding: 2rem;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.08);
        background: white;
    }
    .brand-title {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }
    .brand-sub {
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<div class="brand-title">🔥 FireScope Takeoff Portal</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Private passive fire drawing takeoff system</div>', unsafe_allow_html=True)

    password = st.text_input("Password", type="password")
    if st.button("Enter Portal", type="primary", use_container_width=True):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.authenticated:
    login_screen()
    st.stop()

# -----------------------------
# Default data
# -----------------------------
DEFAULT_RATES = pd.DataFrame([
    ["Hydraulic", "DN50", "Wall", "PVC pipe collar + seal", 43.94],
    ["Hydraulic", "DN65", "Wall", "PVC pipe collar + seal", 55.00],
    ["Hydraulic", "DN80", "Wall", "PVC pipe collar + seal", 68.00],
    ["Hydraulic", "DN100", "Wall", "PVC pipe collar + seal", 85.00],
    ["Hydraulic", "DN150", "Wall", "PVC pipe collar + seal", 135.00],
    ["Hydraulic", "DN50", "Slab", "PVC pipe collar + seal", 55.00],
    ["Hydraulic", "DN100", "Slab", "PVC pipe collar + seal", 110.00],
    ["Electrical", "Small", "Wall", "Mastic seal", 35.00],
    ["Electrical", "Medium", "Wall", "Mastic seal", 65.00],
    ["Electrical", "Cable Tray", "Wall", "Board + mastic", 180.00],
    ["Mechanical", "Small Duct", "Wall", "Board system", 250.00],
    ["Mechanical", "Large Duct", "Wall", "Board system", 650.00],
    ["Fire Rated Joint", "Linear metre", "Wall", "Mastic joint", 18.00],
    ["Board System", "Medium", "Wall", "FR board + seal", 320.00],
], columns=["Service", "Size", "Substrate", "System", "Rate"])

TAKEOFF_COLUMNS = [
    "ID", "Drawing", "Page", "Level", "Area", "Service", "Size", "Substrate",
    "System", "Qty", "Rate", "Value", "X", "Y", "Status", "Notes"
]

if "rates" not in st.session_state:
    st.session_state.rates = DEFAULT_RATES.copy()

if "takeoff" not in st.session_state:
    st.session_state.takeoff = pd.DataFrame(columns=TAKEOFF_COLUMNS)

if "drawing_bytes" not in st.session_state:
    st.session_state.drawing_bytes = None

if "drawing_name" not in st.session_state:
    st.session_state.drawing_name = ""

if "project_meta" not in st.session_state:
    st.session_state.project_meta = {
        "Project Name": "Passive Fire Takeoff",
        "Tender No": "",
        "Client": "",
        "Estimator": "",
        "Revision": "A",
    }

# -----------------------------
# Helpers
# -----------------------------
def pdf_page_to_image(pdf_bytes, page_no, zoom=2):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_no - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

def load_image(uploaded_bytes, name, page_no, zoom):
    if name.lower().endswith(".pdf"):
        return pdf_page_to_image(uploaded_bytes, page_no, zoom)
    return Image.open(io.BytesIO(uploaded_bytes)).convert("RGB")

def resize_for_canvas(img, max_width=1350):
    w, h = img.size
    if w <= max_width:
        return img, 1.0
    scale = max_width / w
    new = img.resize((int(w * scale), int(h * scale)))
    return new, scale

def get_rate(service, size, substrate, system):
    rates = st.session_state.rates
    match = rates[
        (rates["Service"].astype(str).str.lower() == str(service).lower()) &
        (rates["Size"].astype(str).str.lower() == str(size).lower()) &
        (rates["Substrate"].astype(str).str.lower() == str(substrate).lower()) &
        (rates["System"].astype(str).str.lower() == str(system).lower())
    ]
    return float(match.iloc[0]["Rate"]) if len(match) else 0.0

def extract_points_from_canvas(canvas_json, scale, drawing, page, level, area, service, size, substrate, system, status, notes):
    rows = []
    if not canvas_json or "objects" not in canvas_json:
        return rows

    rate = get_rate(service, size, substrate, system)
    for obj in canvas_json["objects"]:
        if obj.get("type") in ["circle", "ellipse"]:
            left = float(obj.get("left", 0))
            top = float(obj.get("top", 0))
            radius = float(obj.get("radius", obj.get("rx", 6)) or 6)
            x = (left + radius) / scale
            y = (top + radius) / scale
            rows.append({
                "ID": "",
                "Drawing": drawing,
                "Page": page,
                "Level": level,
                "Area": area,
                "Service": service,
                "Size": size,
                "Substrate": substrate,
                "System": system,
                "Qty": 1,
                "Rate": rate,
                "Value": rate,
                "X": round(x, 1),
                "Y": round(y, 1),
                "Status": status,
                "Notes": notes
            })
    return rows

def renumber(df):
    df = df.reset_index(drop=True)
    df["ID"] = [f"PF-{i+1:05d}" for i in range(len(df))]
    return df

def recalc(df):
    if df.empty:
        return df
    df = df.copy()
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
    df["Rate"] = pd.to_numeric(df["Rate"], errors="coerce").fillna(0)
    df["Value"] = df["Qty"] * df["Rate"]
    return renumber(df)

def create_summary(df):
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    temp = recalc(df.copy())
    by_system = temp.groupby(["Service", "Size", "Substrate", "System"], dropna=False).agg(
        Qty=("Qty", "sum"), Rate=("Rate", "first"), Value=("Value", "sum")
    ).reset_index()
    by_area = temp.groupby(["Level", "Area"], dropna=False).agg(
        Qty=("Qty", "sum"), Value=("Value", "sum")
    ).reset_index()
    by_drawing = temp.groupby(["Drawing", "Page"], dropna=False).agg(
        Qty=("Qty", "sum"), Value=("Value", "sum")
    ).reset_index()
    return by_system, by_area, by_drawing

def make_marked_image(img, df, scale):
    canvas_img = img.copy()
    draw = ImageDraw.Draw(canvas_img)
    colours = {
        "Hydraulic": "red",
        "Electrical": "blue",
        "Mechanical": "green",
        "Fire Rated Joint": "orange",
        "Board System": "purple",
    }
    for _, r in df.iterrows():
        try:
            x = float(r["X"]) * scale
            y = float(r["Y"]) * scale
        except Exception:
            continue
        service = str(r["Service"])
        colour = colours.get(service, "yellow")
        draw.ellipse((x-7, y-7, x+7, y+7), outline=colour, width=4)
        draw.text((x+9, y-9), str(r["ID"]), fill=colour)
    return canvas_img

def create_excel(df, rates, meta):
    output = io.BytesIO()
    df = recalc(df.copy())
    by_system, by_area, by_drawing = create_summary(df)

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        project_rows = [[k, v] for k, v in meta.items()]
        project_rows += [
            ["Export Date", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Total Count", pd.to_numeric(df["Qty"], errors="coerce").fillna(0).sum() if not df.empty else 0],
            ["Total Value", pd.to_numeric(df["Value"], errors="coerce").fillna(0).sum() if not df.empty else 0],
        ]
        pd.DataFrame(project_rows, columns=["Item", "Value"]).to_excel(writer, index=False, sheet_name="Project")
        df.to_excel(writer, index=False, sheet_name="Clicked Takeoff")
        by_system.to_excel(writer, index=False, sheet_name="Summary by System")
        by_area.to_excel(writer, index=False, sheet_name="Summary by Area")
        by_drawing.to_excel(writer, index=False, sheet_name="Summary by Drawing")
        rates.to_excel(writer, index=False, sheet_name="Rate Library")

        workbook = writer.book
        money = workbook.add_format({"num_format": "$#,##0.00"})
        bold = workbook.add_format({"bold": True})
        for sheet_name, ws in writer.sheets.items():
            ws.freeze_panes(1, 0)
            ws.set_column(0, 22, 18)
        if "Clicked Takeoff" in writer.sheets:
            writer.sheets["Clicked Takeoff"].set_column(10, 11, 14, money)
        if "Summary by System" in writer.sheets:
            writer.sheets["Summary by System"].set_column(4, 5, 14, money)

    return output.getvalue()

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.block-container { padding-top: 1.1rem; }
.metric-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 1rem;
}
.small-note { color: #6b7280; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("## 🔥 FireScope Takeoff Portal")
    st.markdown('<div class="small-note">Private online passive fire click-to-count estimating system</div>', unsafe_allow_html=True)
with top_right:
    if st.button("Log out"):
        st.session_state.authenticated = False
        st.rerun()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Project")
    st.session_state.project_meta["Project Name"] = st.text_input("Project Name", st.session_state.project_meta["Project Name"])
    st.session_state.project_meta["Tender No"] = st.text_input("Tender No", st.session_state.project_meta["Tender No"])
    st.session_state.project_meta["Client"] = st.text_input("Client", st.session_state.project_meta["Client"])
    st.session_state.project_meta["Estimator"] = st.text_input("Estimator", st.session_state.project_meta["Estimator"])
    st.session_state.project_meta["Revision"] = st.text_input("Revision", st.session_state.project_meta["Revision"])

    st.divider()
    uploaded = st.file_uploader("Upload drawing PDF / PNG / JPG", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded:
        st.session_state.drawing_name = uploaded.name
        st.session_state.drawing_bytes = uploaded.read()

    page_no = 1
    zoom = 2
    if st.session_state.drawing_bytes and st.session_state.drawing_name.lower().endswith(".pdf"):
        doc = fitz.open(stream=st.session_state.drawing_bytes, filetype="pdf")
        page_no = st.number_input("PDF Page", min_value=1, max_value=len(doc), value=1)
        zoom = st.slider("PDF Render Zoom", 1, 4, 2)

    st.divider()
    st.header("Current Count Type")
    level = st.text_input("Level", "L01")
    area = st.text_input("Area", "Area A")
    service = st.selectbox("Service", sorted(st.session_state.rates["Service"].dropna().unique().tolist()))
    size_options = sorted(st.session_state.rates[st.session_state.rates["Service"] == service]["Size"].dropna().unique().tolist())
    size = st.selectbox("Size", size_options if size_options else [""])
    substrate = st.selectbox("Substrate", ["Wall", "Slab", "Floor", "Ceiling", "Other"])

    system_options = st.session_state.rates[
        (st.session_state.rates["Service"] == service) &
        (st.session_state.rates["Size"] == size) &
        (st.session_state.rates["Substrate"] == substrate)
    ]["System"].dropna().unique().tolist()
    system = st.selectbox("System", system_options if system_options else sorted(st.session_state.rates["System"].dropna().unique().tolist()))
    status = st.selectbox("Status", ["Measured", "Allowance", "Review", "Excluded"])
    notes = st.text_input("Notes", "")
    point_colour = st.selectbox("Point Colour", ["red", "blue", "green", "orange", "purple", "yellow", "black"])
    point_size = st.slider("Point Size", 6, 20, 10)

# -----------------------------
# Main tabs
# -----------------------------
tabs = st.tabs(["Click Count", "Takeoff Register", "Rates", "Summary", "Export", "Deploy Notes"])

with tabs[0]:
    st.subheader("Click directly on the drawing")

    if not st.session_state.drawing_bytes:
        st.info("Upload a drawing in the sidebar to begin.")
    else:
        original_img = load_image(st.session_state.drawing_bytes, st.session_state.drawing_name, page_no, zoom)
        canvas_img, scale = resize_for_canvas(original_img, max_width=1350)

        st.warning("Use the circle tool. Each circle you draw = one counted item. Add one service/size/system group at a time.")

        canvas_result = st_canvas(
            fill_color="rgba(255, 0, 0, 0.25)",
            stroke_width=3,
            stroke_color=point_colour,
            background_image=canvas_img,
            update_streamlit=True,
            height=canvas_img.height,
            width=canvas_img.width,
            drawing_mode="circle",
            point_display_radius=point_size,
            key=f"canvas_{st.session_state.drawing_name}_{page_no}_{service}_{size}_{substrate}_{system}_{len(st.session_state.takeoff)}"
        )

        clicked = len(canvas_result.json_data["objects"]) if canvas_result.json_data and "objects" in canvas_result.json_data else 0
        rate = get_rate(service, size, substrate, system)

        m1, m2, m3 = st.columns(3)
        m1.metric("Clicked this session", f"{clicked:,}")
        m2.metric("Rate", f"${rate:,.2f}")
        m3.metric("Session Value", f"${clicked * rate:,.2f}")

        if st.button("Add clicked points to takeoff", type="primary"):
            rows = extract_points_from_canvas(
                canvas_result.json_data,
                scale,
                st.session_state.drawing_name,
                page_no,
                level,
                area,
                service,
                size,
                substrate,
                system,
                status,
                notes
            )
            if rows:
                st.session_state.takeoff = renumber(pd.concat([st.session_state.takeoff, pd.DataFrame(rows)], ignore_index=True))
                st.success(f"Added {len(rows)} clicked items to takeoff.")
            else:
                st.warning("No circles found. Draw circles on the drawing first.")

with tabs[1]:
    st.subheader("Takeoff Register")
    st.session_state.takeoff = st.data_editor(
        st.session_state.takeoff,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Qty": st.column_config.NumberColumn("Qty", min_value=0),
            "Rate": st.column_config.NumberColumn("Rate"),
            "Value": st.column_config.NumberColumn("Value", disabled=True),
            "X": st.column_config.NumberColumn("X"),
            "Y": st.column_config.NumberColumn("Y"),
            "Status": st.column_config.SelectboxColumn("Status", options=["Measured", "Allowance", "Review", "Excluded"]),
        }
    )
    if st.button("Recalculate register"):
        st.session_state.takeoff = recalc(st.session_state.takeoff)
        st.success("Register recalculated.")

with tabs[2]:
    st.subheader("Rate Library")
    rate_upload = st.file_uploader("Upload rate library CSV/XLSX", type=["csv", "xlsx"])
    if rate_upload:
        if rate_upload.name.lower().endswith(".csv"):
            st.session_state.rates = pd.read_csv(rate_upload)
        else:
            st.session_state.rates = pd.read_excel(rate_upload)

    st.session_state.rates = st.data_editor(st.session_state.rates, num_rows="dynamic", use_container_width=True)

with tabs[3]:
    st.subheader("Project Summary")
    df = recalc(st.session_state.takeoff.copy()) if not st.session_state.takeoff.empty else st.session_state.takeoff.copy()
    if df.empty:
        st.info("No takeoff yet.")
    else:
        total_qty = pd.to_numeric(df["Qty"], errors="coerce").fillna(0).sum()
        total_value = pd.to_numeric(df["Value"], errors="coerce").fillna(0).sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Count", f"{total_qty:,.0f}")
        c2.metric("Tender Value", f"${total_value:,.2f}")
        c3.metric("Average Rate", f"${(total_value / total_qty if total_qty else 0):,.2f}")

        by_system, by_area, by_drawing = create_summary(df)
        st.write("Summary by System")
        st.dataframe(by_system, use_container_width=True)
        st.write("Summary by Level / Area")
        st.dataframe(by_area, use_container_width=True)
        st.write("Summary by Drawing / Page")
        st.dataframe(by_drawing, use_container_width=True)

with tabs[4]:
    st.subheader("Export")
    df = recalc(st.session_state.takeoff.copy()) if not st.session_state.takeoff.empty else st.session_state.takeoff.copy()

    if df.empty:
        st.info("Add takeoff items first.")
    else:
        excel_data = create_excel(df, st.session_state.rates, st.session_state.project_meta)
        st.download_button(
            "Download Excel Takeoff",
            data=excel_data,
            file_name="firescope_takeoff_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        if st.session_state.drawing_bytes:
            img = load_image(st.session_state.drawing_bytes, st.session_state.drawing_name, page_no, zoom)
            canvas_img, scale = resize_for_canvas(img, max_width=1350)
            page_df = df[df["Page"] == page_no]
            marked = make_marked_image(canvas_img, page_df, scale=scale)
            img_buffer = io.BytesIO()
            marked.save(img_buffer, format="PNG")
            st.image(marked, caption="Marked-up drawing preview", use_container_width=True)
            st.download_button(
                "Download Marked-up Drawing PNG",
                data=img_buffer.getvalue(),
                file_name="firescope_marked_up_drawing.png",
                mime="image/png",
                use_container_width=True
            )

with tabs[5]:
    st.subheader("Online Deployment Notes")
    st.markdown("""
    **Streamlit Cloud setup**
    1. Upload this folder to a private GitHub repository.
    2. Go to Streamlit Cloud and create a new app.
    3. Select `app.py` as the app file.
    4. Add this secret in Streamlit Cloud settings:

    ```toml
    APP_PASSWORD = "your-private-password"
    ```

    **Render setup**
    - Build command: `pip install -r requirements.txt`
    - Start command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

    **Security**
    This is Version 1 password protection. For a commercial app, upgrade to user accounts, database-backed projects, and cloud file storage.
    """)

st.divider()
st.caption("FireScope Takeoff Portal V1 — private online estimating tool. Final quantities must be checked against drawings, specs, revisions, and addenda.")
