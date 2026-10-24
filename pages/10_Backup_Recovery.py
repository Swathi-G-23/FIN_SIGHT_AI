"""
FIN SIGHT AI - Page 10: Project Backup & Disaster Recovery Management
Provides manual snapshot creation, scheduled snapshots, SHA-256 integrity verification,
downloadable archive export, and transparent disaster recovery protocols.
Excludes secrets, credentials, virtual environments, and caches.
"""
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Backup & Recovery | FIN SIGHT AI",
    page_icon="💾",
    layout="wide"
)

from src.ui.theme import (
    apply_light_theme,
    render_sidebar_brand,
    render_page_header,
    render_page_navigation,
)
apply_light_theme()
render_sidebar_brand()

from src.backup.backup_manager import BackupManager

render_page_header(
    title="Backup & Disaster Recovery Management",
    subtitle="Create verified project snapshots, perform SHA-256 checksum checks, and export downloadable recovery archives."
)

backup_mgr = BackupManager()

# ── 1. Backup Creation Section ───────────────────────────────────────────────
st.markdown("### 📦 1. Create Project Backup Snapshot")
st.caption(
    "Archives source code, configurations, database records, document metadata, and vector indices into a verified zip archive. "
    "**Strictly excludes `.env`, secrets, `venv`, and temporary caches.**"
)

col_desc, col_btn = st.columns([3, 1])
with col_desc:
    backup_desc = st.text_input(
        "Backup Description / Release Tag:",
        value="Manual project snapshot",
        placeholder="e.g. Post-upgrade milestone or audited baseline",
    )
with col_btn:
    st.write("")
    st.write("")
    create_clicked = st.button("💾 Create Backup Now", type="primary", use_container_width=True)

if create_clicked:
    with st.spinner("Archiving project files, computing SHA-256 checksums, and building catalog..."):
        try:
            manifest = backup_mgr.create_backup(
                description=backup_desc,
                backup_type="manual",
            )
            st.success(
                f"✅ **Backup Created Successfully:** `{manifest.backup_id}` "
                f"({manifest.total_files} files, {manifest.archive_size_bytes / (1024 * 1024):.2f} MB)"
            )
        except Exception as exc:
            st.error(f"❌ Backup creation failed: {exc}")

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
st.markdown("---")

# ── 2. Backup History & Version Catalog ─────────────────────────────────────
st.markdown("### 📜 2. Backup History & Version Catalog")

backups = backup_mgr.list_backups()

if not backups:
    st.info("No backups currently recorded. Click 'Create Backup Now' above to generate your first snapshot.")
else:
    # Summary KPI cards
    b_k1, b_k2, b_k3, b_k4 = st.columns(4)
    with b_k1:
        st.metric("Total Snapshots", len(backups))
    with b_k2:
        latest = backups[0]
        st.metric("Latest Snapshot", latest["backup_id"])
    with b_k3:
        total_storage = sum(b.get("archive_size_bytes", 0) for b in backups)
        st.metric("Total Storage Used", f"{total_storage / (1024 * 1024):.2f} MB")
    with b_k4:
        st.metric("Integrity Standard", "SHA-256 Hash")

    st.write("")

    catalog_rows = []
    for b in backups:
        created_formatted = b["created_at"][:19].replace("T", " ")
        size_mb = b.get("archive_size_bytes", 0) / (1024 * 1024)
        catalog_rows.append({
            "Backup ID": b["backup_id"],
            "Timestamp": created_formatted,
            "Type": b.get("backup_type", "manual"),
            "Description": b.get("description", ""),
            "Files": b.get("total_files", 0),
            "Size": f"{size_mb:.2f} MB",
            "SHA-256 Hash": b.get("archive_sha256", "")[:12] + "...",
            "Status": "✅ " + b.get("status", "valid").upper(),
        })

    st.dataframe(pd.DataFrame(catalog_rows), use_container_width=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # ── 3. Inspection, Verification & Export ─────────────────────────────────
    st.markdown("### 🔍 3. Snapshot Verification & Archive Export")

    selected_backup_id = st.selectbox(
        "Select Snapshot to Inspect or Export:",
        options=[b["backup_id"] for b in backups],
    )
    selected_entry = next((b for b in backups if b["backup_id"] == selected_backup_id), backups[0])

    act_col1, act_col2, act_col3 = st.columns(3)

    with act_col1:
        st.markdown("##### 1. Integrity Verification")
        if st.button("🛡️ Verify SHA-256 Checksum", use_container_width=True):
            with st.spinner(f"Verifying SHA-256 and zip CRC for {selected_backup_id}..."):
                is_valid, msg, errors = backup_mgr.verify_backup(selected_backup_id)
                if is_valid:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
                    for err in errors:
                        st.caption(f"• {err}")

    with act_col2:
        st.markdown("##### 2. Export Archive")
        archive_bytes = backup_mgr.export_backup_archive(selected_backup_id)
        if archive_bytes:
            st.download_button(
                "📥 Download Backup (.zip)",
                data=archive_bytes,
                file_name=selected_entry.get("archive_filename", f"{selected_backup_id}.zip"),
                mime="application/zip",
                use_container_width=True,
            )
        else:
            st.button("Archive Not Found on Disk", disabled=True, use_container_width=True)

    with act_col3:
        st.markdown("##### 3. Retention Enforcement")
        if st.button("🧹 Enforce Retention Limit", use_container_width=True):
            with st.spinner("Applying retention window (max 15 snapshots)..."):
                cleaned = backup_mgr.enforce_retention_policy(max_backups=15)
                st.success(f"Cleaned {cleaned} older backups outside retention window.")

# ── 4. Safe Disaster Recovery Instructions ───────────────────────────────────
st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("### 🔄 4. Safe Disaster Recovery & Restoration Protocol")
st.markdown(
    """
    <div class="callout-box" style="background:#F8FAFC; border-left-color:#17365D; color:#253247;">
        <b>Integrity Architecture Notice:</b> To prevent file-lock corruption and process race conditions while 
        the Streamlit web server is actively running in Python, system restoration should be performed using the verified 
        exported ZIP archive while the server process is paused.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("📖 Step-by-Step Restoration Protocol", expanded=True):
    st.markdown(
        """
        1. **Download or locate the verified backup archive:**
           Click **'Download Backup (.zip)'** above or locate the file in `backups/` (e.g. `backups/backup_20261023_132204.zip`).
        2. **Stop the active server:**
           In your terminal running Streamlit, press `Ctrl + C`.
        3. **Extract archive over the project folder:**
           ```powershell
           # In PowerShell (Windows):
           Expand-Archive -Path backups/<YOUR_BACKUP_ID>.zip -DestinationPath . -Force
           ```
        4. **Verify integrity and re-launch:**
           ```powershell
           .\venv\Scripts\pytest.exe tests/ -q
           .\venv\Scripts\streamlit.exe run app.py
           ```
        """
    )

# ── Standard Page Navigation ─────────────────────────────────────────────────
render_page_navigation(
    prev_page="pages/9_System_Performance.py",
    next_page=None,
    prev_label="System Performance",
)
