"""AI Analysis page - model registry and prediction interface."""

import streamlit as st

from ai import AIService
from core.config import get_config
from core.logging import get_logger
from ui.components import info_box, metric_card, section_header
from ui.theme import apply_theme

logger = get_logger(__name__)
config = get_config()

st.set_page_config(page_title="AI Analysis", page_icon="🧠", layout="wide")
apply_theme()

st.title("🧠 AI Analysis")
st.caption("AI-powered CFD analysis and prediction")

# ============================================================
# SERVICE
# ============================================================

service = AIService()
status = service.get_status()

# ============================================================
# STATUS PANEL
# ============================================================

section_header("AI System Status", "Current state of the AI subsystem", icon="📡")

col1, col2, col3 = st.columns(3)

with col1:
    if status.ready:
        metric_card("Status", "Ready", icon="🟢")
    elif status.model_count > 0:
        metric_card("Status", "Models Available", icon="🟡")
    else:
        metric_card("Status", "Awaiting Model", icon="⚪")

with col2:
    metric_card("Registered Models", str(status.model_count), icon="📦")

with col3:
    active = status.active_model_name or "None"
    metric_card("Active Model", active, icon="🎯")

# ============================================================
# HONEST MESSAGING
# ============================================================

if not status.ready:
    if status.model_count == 0:
        info_box(
            "<b>No AI model is configured yet.</b><br>"
            "This page is ready to host real PyTorch / NVIDIA Modulus models. "
            "When a model is registered, its predictions will appear here.",
            "info",
        )
    else:
        info_box(
            f"<b>{status.model_count} model(s)</b> are registered but none is active. "
            f"Select one below to activate it.",
            "warning",
        )
else:
    info_box(
        f"✅ Model <b>{status.active_model_name}</b> is active and ready for predictions.",
        "success",
    )

# ============================================================
# REGISTERED MODELS
# ============================================================

section_header("Registered Models", "Available AI models", icon="📦")

models = service.list_available_models()

if not models:
    st.markdown("**No models registered yet.**")
    st.markdown("To register a model, run this in PowerShell (venv active):")
    st.code(
        'python -c "from ai import ModelMetadata, register_model; '
        "m = ModelMetadata(model_id='test-surrogate-v1', "
        "name='Cylinder Flow Surrogate', version='1.0.0', "
        "model_type='FNO', description='Predicts flow around cylinder', "
        "input_features=['inlet_velocity'], output_features=['max_velocity'], "
        "training_metrics={'rmse': 0.012}, validation_metrics={'rmse': 0.018}); "
        "register_model(m); print('Registered')\"",
        language="powershell",
    )
else:
    for model in models:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.markdown(f"### {model.name}")
                st.caption(f"ID: `{model.model_id}`")
                if model.description:
                    st.caption(model.description)

            with col2:
                st.markdown(f"**Type:** {model.model_type}")
                st.markdown(f"**Version:** {model.version}")

            with col3:
                if model.training_metrics:
                    rmse = model.training_metrics.get("rmse", "N/A")
                    st.markdown(f"**Train RMSE:** {rmse}")
                if model.validation_metrics:
                    rmse = model.validation_metrics.get("rmse", "N/A")
                    st.markdown(f"**Val RMSE:** {rmse}")

            with col4:
                is_active = model.model_id == status.active_model_id
                btn_type = "secondary" if is_active else "primary"
                if st.button(
                    "Active" if is_active else "Activate",
                    key=f"activate_{model.model_id}",
                    use_container_width=True,
                    type=btn_type,
                    disabled=is_active,
                ):
                    try:
                        service.activate_model(model.model_id)
                        st.success(f"Activated: {model.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

            st.markdown("---")

# ============================================================
# PREDICTION INTERFACE
# ============================================================

section_header(
    "Prediction Interface", "Run a prediction with the active model", icon="🎯"
)

if not status.ready:
    info_box("Predictions are disabled until a model is activated.", "info")
else:
    st.markdown("**Input Parameters**")

    col1, col2 = st.columns(2)
    with col1:
        inlet_velocity = st.number_input(
            "Inlet Velocity (m/s)", value=10.0, min_value=0.1
        )
        temperature = st.number_input("Temperature (K)", value=293.15, min_value=1.0)
    with col2:
        pressure = st.number_input("Pressure (Pa)", value=101325.0, min_value=1.0)
        fluid = st.selectbox("Fluid", ["Air", "Water"])

    if st.button("🔮 Predict", type="primary"):
        try:
            result = service.predict(
                {
                    "inlet_velocity": inlet_velocity,
                    "temperature": temperature,
                    "pressure": pressure,
                    "fluid": fluid,
                }
            )

            st.success("✅ Prediction complete")

            col1, col2, col3 = st.columns(3)
            with col1:
                metric_card("Model", result.model_name, icon="🧠")
            with col2:
                conf = f"{result.confidence:.2%}" if result.confidence else "N/A"
                metric_card("Confidence", conf, icon="📊")
            with col3:
                metric_card("Timestamp", result.timestamp[11:19], icon="⏱️")

            st.markdown("**Result:**")
            st.json(result.prediction)

        except Exception as e:
            st.error(f"❌ Prediction failed: {e}")

# ============================================================
# ROADMAP
# ============================================================

section_header("AI Roadmap", "Planned capabilities", icon="🗺️")

st.markdown("""
    The AI subsystem is designed for these future capabilities:

    | Feature | Status | Notes |
    |---------|--------|-------|
    | Model registry | Ready | Register trained models via Python API |
    | Model activation | Ready | Select active model for predictions |
    | Prediction interface | Ready | Plug in any PyTorch model |
    | Real PyTorch integration | Next | Load .pt files and run inference |
    | NVIDIA Modulus (PINN) | Future | Physics-informed networks |
    | Surrogate modeling | Future | Fast approximations of CFD runs |
    | Parameter optimization | Future | Auto-tune design variables |
    | Anomaly detection | Future | Flag unusual flow patterns |

    **Note:** All AI predictions will be traceable to the specific model and version.
    """)
