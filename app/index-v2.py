# -*- coding: utf-8 -*-
import streamlit as st
import pynetbox
import requests
import os
import base64
import ipaddress
from dotenv import load_dotenv
import urllib3
import time


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()


st.set_page_config(
    page_title="Portal NetBox + AWX",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# IDENTIFICACAO DO USUARIO
# ============================================================================

def obter_usuario():
    headers = st.context.headers
    usuario = headers.get("X-Remote-User", "")
    nome    = headers.get("X-Remote-Name", "")
    email   = headers.get("X-Remote-Email", "")

    if not usuario:
        auth_header = headers.get("Authorization", "")
        if auth_header.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                usuario = decoded.split(":")[0]
            except Exception:
                usuario = "unknown"

    if not usuario:
        usuario = "unknown"
    if not nome:
        nome = usuario

    return {"usuario": usuario, "nome": nome, "email": email}


usuario_info = obter_usuario()

# ============================================================================
# CSS LIGHT PROFISSIONAL
# ============================================================================

st.markdown("""
<style>
    /* Fundo geral */
    .stApp {
        background-color: #f8fafc;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #0f2444 100%);
        border-right: 3px solid #2563eb;
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #334d6e !important;
    }
    [data-testid="stSidebar"] .stCaption {
        color: #94a3b8 !important;
    }

    /* Titulo principal */
    h1 {
        background: linear-gradient(90deg, #1d4ed8 0%, #0369a1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem !important;
        letter-spacing: -0.5px;
    }

    /* Subtitulos */
    h2 {
        color: #1e3a5f !important;
        font-weight: 700;
        border-bottom: 2px solid #2563eb;
        padding-bottom: 8px;
    }
    h3 {
        color: #1e40af !important;
        font-weight: 600;
    }

    /* Botoes primarios */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
        transform: translateY(-1px);
    }

    /* Botoes secundarios */
    .stButton > button:not([kind="primary"]) {
        background: white;
        color: #1e3a5f !important;
        border: 1.5px solid #cbd5e1;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:not([kind="primary"]):hover {
        border-color: #2563eb;
        color: #2563eb !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
        transform: translateY(-1px);
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background: white;
        border: 1.5px solid #e2e8f0;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        overflow: hidden;
    }
    [data-testid="stExpander"]:hover {
        border-color: #93c5fd;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
    }
    [data-testid="stExpander"] summary {
        font-weight: 600;
        color: #1e3a5f !important;
        font-size: 1rem;
        padding: 0.75rem 1rem;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        border: 1.5px solid #cbd5e1;
        border-radius: 8px;
        background: white;
        color: #0f172a;
        transition: border-color 0.2s;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }

    /* Selectbox */
    .stSelectbox > div > div {
        border: 1.5px solid #cbd5e1;
        border-radius: 8px;
        background: white;
    }

    /* Mensagens de status */
    [data-testid="stAlert"] {
        border-radius: 10px;
        border-left-width: 4px;
        font-weight: 500;
    }

    /* Divisores */
    hr {
        border-color: #e2e8f0 !important;
    }

    /* Radio */
    .stRadio > div {
        background: white;
        border: 1.5px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.5rem 1rem;
    }

    /* Code block */
    .stCode {
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONFIGURACOES
# ============================================================================

NETBOX_URL           = os.getenv("NETBOX_URL")
NETBOX_TOKEN         = os.getenv("NETBOX_TOKEN")
AWX_URL              = os.getenv("AWX_URL")
AWX_USER             = os.getenv("AWX_USER")
AWX_PASSWORD         = os.getenv("AWX_PASSWORD")

PREFIXO_PAI_INTERNAL   = "10.101.0.0/16"
PREFIXO_PAI_TRANSIT    = "100.64.0.0/23"
BGP_ASN                = "65001"
ROUTE_POLICY           = "RP_DENY-CGNAT_DC"
VRF_ROUTETARGET_IMPORT = "1:1900"

# ============================================================================
# CONEXAO NETBOX
# ============================================================================

@st.cache_resource
def conectar_netbox():
    try:
        nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
        nb.http_session.verify = False
        _ = nb.version
        return nb, None
    except Exception as e:
        return None, str(e)

nb, erro_nb = conectar_netbox()

# ============================================================================
# FUNCOES NETBOX
# ============================================================================

def listar_tenant_groups():
    try:
        return list(nb.tenancy.tenant_groups.all()), None
    except Exception as e:
        return [], str(e)

def criar_tenant(nome, slug, group_id=None, descricao=""):
    try:
        dados = {'name': nome, 'slug': slug}
        if group_id:
            dados['group'] = group_id
        if descricao:
            dados['description'] = descricao
        return nb.tenancy.tenants.create(**dados), None
    except Exception as e:
        return None, str(e)

def criar_vrf(nome, rd, tenant_id, descricao=""):
    try:
        dados = {'name': nome, 'rd': rd, 'tenant': tenant_id}
        if descricao:
            dados['description'] = descricao
        return nb.ipam.vrfs.create(**dados), None
    except Exception as e:
        return None, str(e)

def buscar_vlans_disponiveis(vlan_inicio, vlan_fim):
    try:
        filtro            = {'vid__gte': vlan_inicio, 'vid__lte': vlan_fim}
        vlans_cadastradas = list(nb.ipam.vlans.filter(**filtro))
        vlans_usadas      = {vlan.vid for vlan in vlans_cadastradas}
        todas_vlans       = set(range(vlan_inicio, vlan_fim + 1))
        vlans_disponiveis = sorted(todas_vlans - vlans_usadas)
        return vlans_disponiveis, vlans_cadastradas, None
    except Exception as e:
        return None, None, str(e)

def alocar_vlan(vid, nome, tenant_id, descricao=""):
    try:
        dados = {'vid': vid, 'name': nome, 'tenant': tenant_id, 'status': 'activ                                                                                        e'}
        if descricao:
            dados['description'] = descricao
        return nb.ipam.vlans.create(**dados), None
    except Exception as e:
        return None, str(e)

def buscar_prefixos_disponiveis(prefixo_pai, mascara):
    """
    Busca prefixos disponiveis dentro do prefixo pai com a mascara exata.
    1. Busca todos os sub-prefixos ja alocados dentro do pai via API
    2. Calcula manualmente quais /mascara ainda estao livres
    3. Retorna apenas os prefixos com a mascara exata solicitada
    """
    try:
        rede_pai     = ipaddress.ip_network(prefixo_pai, strict=False)
        alocados_raw = list(nb.ipam.prefixes.filter(within=prefixo_pai))
        alocados     = [ipaddress.ip_network(str(p.prefix), strict=False) for p                                                                                         in alocados_raw]
        candidatos   = list(rede_pai.subnets(new_prefix=mascara))

        disponiveis = []
        for candidato in candidatos:
            sobreposto = any(candidato.overlaps(alocado) for alocado in alocados                                                                                        )
            if not sobreposto:
                disponiveis.append(str(candidato))

        return disponiveis, None
    except Exception as e:
        return None, str(e)

def alocar_prefixo(prefixo, tenant_id, descricao=""):
    try:
        dados = {'prefix': prefixo, 'tenant': tenant_id, 'status': 'active'}
        if descricao:
            dados['description'] = descricao
        return nb.ipam.prefixes.create(**dados), None
    except Exception as e:
        return None, str(e)

# ============================================================================
# FUNCOES AWX
# ============================================================================

def listar_job_templates():
    try:
        from requests.auth import HTTPBasicAuth
        url      = f"{AWX_URL}/api/v2/job_templates/"
        response = requests.get(url, auth=HTTPBasicAuth(AWX_USER, AWX_PASSWORD),
                                verify=False, timeout=10)
        if response.status_code == 200:
            return response.json().get('results', []), None
        return None, f"Erro {response.status_code}"
    except Exception as e:
        return None, str(e)

def disparar_job_template(template_id, extra_vars):
    try:
        from requests.auth import HTTPBasicAuth
        url      = f"{AWX_URL}/api/v2/job_templates/{template_id}/launch/"
        response = requests.post(url, auth=HTTPBasicAuth(AWX_USER, AWX_PASSWORD)                                                                                        ,
                                 json={"extra_vars": extra_vars}, verify=False)
        if response.status_code in [200, 201]:
            job_data = response.json()
            return job_data.get('id'), f"{AWX_URL}/#/jobs/playbook/{job_data.get                                                                                        ('id')}", None
        try:
            return None, None, f"Erro {response.status_code}: {response.json()}"
        except Exception:
            return None, None, f"Erro {response.status_code}: {response.text}"
    except Exception as e:
        return None, None, str(e)

def verificar_status_job(job_id):
    try:
        from requests.auth import HTTPBasicAuth
        url      = f"{AWX_URL}/api/v2/jobs/{job_id}/"
        response = requests.get(url, auth=HTTPBasicAuth(AWX_USER, AWX_PASSWORD),                                                                                         verify=False)
        if response.status_code == 200:
            return response.json().get('status'), None
        return None, f"Erro {response.status_code}"
    except Exception as e:
        return None, str(e)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 10px 0 20px 0;'>
        <div style='font-size: 2.5rem;'>🌐</div>
        <div style='font-size: 1.1rem; font-weight: 700; color: #e2e8f0; letter-                                                                                        spacing: 0.5px;'>NetBox + AWX</div>
        <div style='font-size: 0.75rem; color: #94a3b8; margin-top: 2px;'>Portal                                                                                         de Automação</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background: rgba(255,255,255,0.07); border-radius: 10px; padding                                                                                        : 14px 16px; margin-bottom: 12px;'>
        <div style='font-size: 0.7rem; text-transform: uppercase; letter-spacing                                                                                        : 1px;
                    color: #64748b; margin-bottom: 8px;'>Sessão Ativa</div>
    """, unsafe_allow_html=True)
    st.write(f"👤 **{usuario_info['nome']}**")
    if usuario_info['email']:
        st.write(f"✉️ {usuario_info['email']}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align: center; margin-top: 8px;'>
        <span style='background: rgba(34,197,94,0.15); color: #4ade80; border-ra                                                                                        dius: 99px;
                     padding: 3px 12px; font-size: 0.75rem; font-weight: 600;'>
            🔒 LDAP / Nginx
        </span>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# CABECALHO
# ============================================================================

st.markdown("""
<div style='text-align: center; padding: 18px 0 6px 0;'>
    <div style='display:inline-flex; align-items:center; gap:12px;'>
        <svg width='32' height='32' viewBox='0 0 24 24' fill='none' xmlns='http:                                                                                        //www.w3.org/2000/svg'>
            <circle cx='12' cy='12' r='3' fill='#2563eb'/>
            <circle cx='4' cy='6' r='2' fill='#93c5fd'/>
            <circle cx='20' cy='6' r='2' fill='#93c5fd'/>
            <circle cx='4' cy='18' r='2' fill='#93c5fd'/>
            <circle cx='20' cy='18' r='2' fill='#93c5fd'/>
            <line x1='6' y1='7' x2='10' y2='10' stroke='#2563eb' stroke-width='1                                                                                        .5' stroke-linecap='round'/>
            <line x1='18' y1='7' x2='14' y2='10' stroke='#2563eb' stroke-width='                                                                                        1.5' stroke-linecap='round'/>
            <line x1='6' y1='17' x2='10' y2='14' stroke='#2563eb' stroke-width='                                                                                        1.5' stroke-linecap='round'/>
            <line x1='18' y1='17' x2='14' y2='14' stroke='#2563eb' stroke-width=                                                                                        '1.5' stroke-linecap='round'/>
        </svg>
        <h1 style='margin:0; display:inline;'>Portal de Automação</h1>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    f"<p style='text-align: center; font-size: 1.05rem; color: #475569; margin-b                                                                                        ottom: 0;'>"
    f"Bem-vindo, <strong>{usuario_info['nome']}</strong>!</p>",
    unsafe_allow_html=True
)
st.markdown("---")

if erro_nb:
    st.error(f"❌ Falha ao conectar no NetBox: {erro_nb}")
    st.stop()

# ============================================================================
# STATUS CARDS
# ============================================================================

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div style='background:white; border:1.5px solid #e2e8f0; border-left:4px so                                                                                        lid #2563eb;
                border-radius:12px; padding:18px 22px; display:flex; align-items                                                                                        :center;
                gap:16px; box-shadow:0 1px 6px rgba(0,0,0,0.06);'>
        <img src='https://avatars.githubusercontent.com/u/20414678'
             style='width:44px;height:44px;border-radius:10px;object-fit:cover;f                                                                                        lex-shrink:0;'
             onerror="this.style.display='none'"/>
        <div style='flex:1; min-width:0;'>
            <div style='font-size:0.7rem; text-transform:uppercase; letter-spaci                                                                                        ng:1.2px;
                        color:#2563eb; font-weight:700; margin-bottom:2px;'>NetB                                                                                        ox</div>
            <div style='font-size:1rem; font-weight:700; color:#0f172a;'>NetBox                                                                                         Community</div>
            <div style='font-size:0.78rem; color:#64748b; margin-top:1px;'>Versa                                                                                        o {nb.version} &nbsp;·&nbsp; IPAM / DCIM</div>
        </div>
        <span style='background:#dcfce7; color:#15803d; border-radius:99px;
                     padding:4px 12px; font-size:0.72rem; font-weight:700; white                                                                                        -space:nowrap;'>
            ● Online
        </span>
    </div>
    """, unsafe_allow_html=True)

with col2:
    try:
        templates_check, _ = listar_job_templates()
        if templates_check:
            st.markdown(f"""
            <div style='background:white; border:1.5px solid #e2e8f0; border-lef                                                                                        t:4px solid #7c3aed;
                        border-radius:12px; padding:18px 22px; display:flex; ali                                                                                        gn-items:center;
                        gap:16px; box-shadow:0 1px 6px rgba(0,0,0,0.06);'>
                <img src='https://avatars.githubusercontent.com/u/1507452'
                     style='width:44px;height:44px;border-radius:10px;object-fit                                                                                        :cover;flex-shrink:0;'
                     onerror="this.style.display='none'"/>
                <div style='flex:1; min-width:0;'>
                    <div style='font-size:0.7rem; text-transform:uppercase; lett                                                                                        er-spacing:1.2px;
                                color:#7c3aed; font-weight:700; margin-bottom:2p                                                                                        x;'>AWX / Ansible</div>
                    <div style='font-size:1rem; font-weight:700; color:#0f172a;'                                                                                        >Ansible AWX</div>
                    <div style='font-size:0.78rem; color:#64748b; margin-top:1px                                                                                        ;'>{len(templates_check)} Job Templates &nbsp;·&nbsp; Automacao</div>
                </div>
                <span style='background:#dcfce7; color:#15803d; border-radius:99                                                                                        px;
                             padding:4px 12px; font-size:0.72rem; font-weight:70                                                                                        0; white-space:nowrap;'>
                    ● Online
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ AWX nao configurado")
    except Exception:
        st.warning("⚠️ AWX nao configurado")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ============================================================================
# SESSION STATE
# Nova ordem: tenant → vlan_internal → vlan_transit → vrf → prefixo_24 → prefixo                                                                                        _30
# ============================================================================

for key in ['tenant_criado', 'vlan_internal_alocada', 'vlan_transit_alocada',
            'vrf_criada', 'prefixo_24_alocado', 'prefixo_30_alocado']:
    if key not in st.session_state:
        st.session_state[key] = None

# ============================================================================
# BARRA DE PROGRESSO CUSTOMIZADA
# ============================================================================

etapas_completas = sum([
    st.session_state.tenant_criado         is not None,
    st.session_state.vlan_internal_alocada is not None,
    st.session_state.vlan_transit_alocada  is not None,
    st.session_state.vrf_criada            is not None,
    st.session_state.prefixo_24_alocado    is not None,
    st.session_state.prefixo_30_alocado    is not None,
])

pct = int((etapas_completas / 6) * 100)

# Labels na nova ordem
ETAPAS_LABELS = ["Tenant", "VLAN Int.", "VLAN Tran.", "VRF", "Prefixo /24", "Pre                                                                                        fixo /30"]

import streamlit.components.v1 as components

etapas_steps = ""
for i, label in enumerate(ETAPAS_LABELS):
    concluido   = i < etapas_completas
    cor_circulo = "background:linear-gradient(135deg,#2563eb,#0ea5e9);" if concl                                                                                        uido else "background:#e2e8f0;"
    cor_texto   = "#2563eb" if concluido else "#94a3b8"
    peso_texto  = "700" if concluido else "400"
    simbolo     = "&#10003;" if concluido else str(i + 1)
    cor_simbolo = "white" if concluido else "#94a3b8"
    sombra      = "0 2px 8px rgba(37,99,235,0.3)" if concluido else "none"
    etapas_steps += (
        "<div style='display:flex;flex-direction:column;align-items:center;gap:4                                                                                        px;flex:1;'>"
        "<div style='width:28px;height:28px;border-radius:50%;" + cor_circulo
        + "display:flex;align-items:center;justify-content:center;"
        "font-size:0.75rem;font-weight:700;color:" + cor_simbolo
        + ";box-shadow:" + sombra + ";'>" + simbolo + "</div>"
        "<div style='font-size:0.65rem;color:" + cor_texto
        + ";font-weight:" + peso_texto
        + ";text-align:center;white-space:nowrap;'>" + label + "</div>"
        "</div>"
    )

badge_bg    = "#dcfce7" if etapas_completas == 6 else "#eff6ff"
badge_color = "#15803d" if etapas_completas == 6 else "#2563eb"
badge_text  = str(etapas_completas) + "/6 &#10003; Completo" if etapas_completas                                                                                         == 6 else str(etapas_completas) + "/6 etapas"

# Build stepper with connecting bar
# Relative container: circles on top, bar behind them
pct_str = str(pct)

progress_html = (
    "<div style='font-family:Inter,sans-serif;background:white;border:1.5px soli                                                                                        d #e2e8f0;"
    "border-radius:16px;padding:20px 28px;box-shadow:0 1px 6px rgba(0,0,0,0.05);                                                                                        '>"
    # Header row
    "<div style='display:flex;justify-content:space-between;align-items:center;m                                                                                        argin-bottom:20px;'>"
    "<span style='font-weight:700;color:#1e3a5f;font-size:0.95rem;'>Progresso do                                                                                         Provisionamento</span>"
    "<span style='background:" + badge_bg + ";color:" + badge_color
    + ";border-radius:99px;padding:3px 14px;font-size:0.78rem;font-weight:700;'>                                                                                        "
    + badge_text + "</span></div>"
    # Progress bar track
    "<div style='background:#e2e8f0;border-radius:99px;height:6px;margin-bottom:                                                                                        10px;overflow:hidden;'>"
    "<div style='background:linear-gradient(90deg,#2563eb,#0ea5e9);height:100%;b                                                                                        order-radius:99px;"
    "width:" + pct_str + "%;transition:width 0.4s ease;'></div></div>"
    # Stepper circles + labels
    "<div style='display:flex;align-items:flex-start;justify-content:space-betwe                                                                                        en;'>"
    + etapas_steps
    + "</div></div>"
)

components.html(progress_html, height=150)
st.markdown("---")

# ============================================================================
# ETAPA 1: TENANT
# ============================================================================

with st.expander("1️⃣  Criar Tenant", expanded=(st.session_state.tenant_criado is                                                                                         None)):
    if st.session_state.tenant_criado:
        st.success(f"✅ Tenant: **{st.session_state.tenant_criado['nome']}**")
        if st.button("🔄 Resetar tudo", key="reset_tenant"):
            for key in ['tenant_criado', 'vlan_internal_alocada', 'vlan_transit_                                                                                        alocada',
                        'vrf_criada', 'prefixo_24_alocado', 'prefixo_30_alocado'                                                                                        ]:
                st.session_state[key] = None
            st.rerun()
    else:
        groups, _ = listar_tenant_groups()
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome:", placeholder="Empresa ABC", key="nome_t                                                                                        enant")
            slug = st.text_input("Slug:", placeholder="empresa-abc", key="slug_t                                                                                        enant")
        with col2:
            if groups:
                group_opt = ["Nenhum"] + [f"{g.name} (ID: {g.id})" for g in grou                                                                                        ps]
                group_sel = st.selectbox("Grupo:", group_opt, key="group_tenant"                                                                                        )
                group_id  = None if group_sel == "Nenhum" else int(group_sel.spl                                                                                        it("ID: ")[1].rstrip(")"))
            else:
                group_id = None
            desc = st.text_area("Descricao:", key="desc_tenant")

        if st.button("✅ Criar Tenant", type="primary", key="btn_criar_tenant"):
            if nome and slug:
                tenant, erro = criar_tenant(nome, slug, group_id, desc)
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.tenant_criado = {'id': tenant.id, 'nome': t                                                                                        enant.name, 'slug': tenant.slug}
                    st.success("✅ Criado!")
                    st.balloons()
                    st.rerun()
            else:
                st.error("❌ Preencha nome e slug")

# ============================================================================
# ETAPA 2: VLAN INTERNAL  (antes era etapa 3)
# ============================================================================

with st.expander("2️⃣  VLAN Internal", expanded=(
        st.session_state.tenant_criado is not None and st.session_state.vlan_int                                                                                        ernal_alocada is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.vlan_internal_alocada:
        v = st.session_state.vlan_internal_alocada
        st.success(f"✅ VLAN {v['vid']} — {v['nome']}")
    else:
        tenant = st.session_state.tenant_criado
        col1, col2, col3 = st.columns(3)
        with col1:
            inicio = st.number_input("Inicio:", 1, 4094, 100, key="vlan_int_inic                                                                                        io")
        with col2:
            fim    = st.number_input("Fim:", 1, 4094, 500, key="vlan_int_fim")
        with col3:
            st.write("")
            st.write("")
            buscar = st.button("🔍 Buscar", key="btn_buscar_vlan_int")

        if buscar:
            disp, cad, erro = buscar_vlans_disponiveis(inicio, fim)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.vlans_int_disp = disp

        if st.session_state.get('vlans_int_disp'):
            disp      = st.session_state.vlans_int_disp
            st.success(f"✅ {len(disp)} VLANs disponiveis")
            st.write(', '.join(map(str, disp[:30])))
            vlan_sel  = st.selectbox("VLAN:", disp[:50], key="vlan_int_sel")
            nome_vlan = st.text_input("Nome:", value=f"VLAN_{tenant['slug'].uppe                                                                                        r()}_{vlan_sel}_INT",
                                      key="vlan_int_nome")
            if st.button("✅ Alocar", type="primary", key="btn_alocar_vlan_int")                                                                                        :
                vlan, erro = alocar_vlan(vlan_sel, nome_vlan, tenant['id'])
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.vlan_internal_alocada = {'id': vlan.id, 'vi                                                                                        d': vlan.vid, 'nome': vlan.name}
                    st.success("✅ Alocada!")
                    st.balloons()
                    st.rerun()

# ============================================================================
# ETAPA 3: VLAN TRANSIT  (antes era etapa 4)
# ============================================================================

with st.expander("3️⃣  VLAN Transit", expanded=(
        st.session_state.vlan_internal_alocada is not None and st.session_state.                                                                                        vlan_transit_alocada is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.vlan_transit_alocada:
        v = st.session_state.vlan_transit_alocada
        st.success(f"✅ VLAN {v['vid']} — {v['nome']}")
    else:
        tenant = st.session_state.tenant_criado
        col1, col2, col3 = st.columns(3)
        with col1:
            inicio = st.number_input("Inicio:", 1, 4094, 800, key="vlan_tran_ini                                                                                        cio")
        with col2:
            fim    = st.number_input("Fim:", 1, 4094, 900, key="vlan_tran_fim")
        with col3:
            st.write("")
            st.write("")
            buscar = st.button("🔍 Buscar", key="btn_buscar_vlan_tran")

        if buscar:
            disp, cad, erro = buscar_vlans_disponiveis(inicio, fim)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.vlans_tran_disp = disp

        if st.session_state.get('vlans_tran_disp'):
            disp      = st.session_state.vlans_tran_disp
            st.success(f"✅ {len(disp)} VLANs disponiveis")
            st.write(', '.join(map(str, disp[:30])))
            vlan_sel  = st.selectbox("VLAN:", disp[:50], key="vlan_tran_sel")
            nome_vlan = st.text_input("Nome:", value=f"VLAN_{tenant['slug'].uppe                                                                                        r()}_{vlan_sel}_TRAN",
                                      key="vlan_tran_nome")
            if st.button("✅ Alocar", type="primary", key="btn_alocar_vlan_tran"                                                                                        ):
                vlan, erro = alocar_vlan(vlan_sel, nome_vlan, tenant['id'])
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.vlan_transit_alocada = {'id': vlan.id, 'vid                                                                                        ': vlan.vid, 'nome': vlan.name}
                    st.success("✅ Alocada!")
                    st.balloons()
                    st.rerun()

# ============================================================================
# ETAPA 4: VRF  (antes era etapa 2)
# RD pre-preenchido com base na VLAN interna: BGP_ASN:VLAN_ID
# ============================================================================

with st.expander("4️⃣  Criar VRF", expanded=(
        st.session_state.vlan_transit_alocada is not None and st.session_state.v                                                                                        rf_criada is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif not st.session_state.vlan_internal_alocada:
        st.warning("⚠️ Aloque a VLAN Internal primeiro para definir o RD")
    elif st.session_state.vrf_criada:
        st.success(f"✅ VRF: **{st.session_state.vrf_criada['nome']}** — RD: `{s                                                                                        t.session_state.vrf_criada['rd']}`")
    else:
        tenant   = st.session_state.tenant_criado
        vlan_int = st.session_state.vlan_internal_alocada

        # RD sugerido automaticamente com base na VLAN interna
        rd_sugerido = f"{BGP_ASN}:{vlan_int['vid']}"

        st.info(f"💡 RD sugerido com base na VLAN Internal **{vlan_int['vid']}**                                                                                        : `{rd_sugerido}`")

        col1, col2 = st.columns(2)
        with col1:
            nome_vrf = st.text_input("Nome VRF:", value=f"VRF_{tenant['slug'].up                                                                                        per()}", key="nome_vrf")
            rd       = st.text_input("RD:", value=rd_sugerido, key="rd_vrf")
        with col2:
            desc_vrf = st.text_area("Descricao:", key="desc_vrf")

        if st.button("✅ Criar VRF", type="primary", key="btn_criar_vrf"):
            if nome_vrf and rd:
                vrf, erro = criar_vrf(nome_vrf, rd, tenant['id'], desc_vrf)
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.vrf_criada = {'id': vrf.id, 'nome': vrf.nam                                                                                        e, 'rd': vrf.rd}
                    st.success("✅ Criada!")
                    st.balloons()
                    st.rerun()
            else:
                st.error("❌ Preencha todos os campos")

# ============================================================================
# ETAPA 5: PREFIXO /24
# ============================================================================

with st.expander("5️⃣  Prefixo /24", expanded=(
        st.session_state.vrf_criada is not None and st.session_state.prefixo_24_                                                                                        alocado is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.prefixo_24_alocado:
        st.success(f"✅ {st.session_state.prefixo_24_alocado['prefixo']}")
    else:
        tenant = st.session_state.tenant_criado
        st.info(f"ℹ️ Prefixo Pai: **{PREFIXO_PAI_INTERNAL}**")

        if st.button("🔍 Buscar /24", key="btn_buscar_24"):
            with st.spinner("Buscando prefixos /24 disponiveis..."):
                disp, erro = buscar_prefixos_disponiveis(PREFIXO_PAI_INTERNAL, 2                                                                                        4)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.prefixos_24 = disp

        if st.session_state.get('prefixos_24'):
            disp = st.session_state.prefixos_24
            if disp:
                st.success(f"✅ {len(disp)} prefixos /24 disponiveis")
                for i, p in enumerate(disp[:20], 1):
                    st.write(f"{i}. {p}")
                if len(disp) > 20:
                    st.caption(f"... e mais {len(disp) - 20}")
                pref_sel = st.selectbox("Prefixo:", disp[:50], key="pref_24_sel"                                                                                        )
                if st.button("✅ Alocar", type="primary", key="btn_alocar_24"):
                    with st.spinner("Alocando..."):
                        pref, erro = alocar_prefixo(pref_sel, tenant['id'])
                    if erro:
                        st.error(f"❌ {erro}")
                    else:
                        st.session_state.prefixo_24_alocado = {'id': pref.id, 'p                                                                                        refixo': str(pref.prefix)}
                        st.success("✅ Alocado!")
                        st.balloons()
                        st.rerun()
            else:
                st.warning("⚠️ Nenhum prefixo /24 disponivel")

# ============================================================================
# ETAPA 6: PREFIXO /30
# ============================================================================

with st.expander("6️⃣  Prefixo /30", expanded=(
        st.session_state.prefixo_24_alocado is not None and st.session_state.pre                                                                                        fixo_30_alocado is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.prefixo_30_alocado:
        st.success(f"✅ {st.session_state.prefixo_30_alocado['prefixo']}")
    else:
        tenant = st.session_state.tenant_criado
        st.info(f"ℹ️ Prefixo Pai: **{PREFIXO_PAI_TRANSIT}**")

        if st.button("🔍 Buscar /30", key="btn_buscar_30"):
            with st.spinner("Buscando prefixos /30 disponiveis..."):
                disp, erro = buscar_prefixos_disponiveis(PREFIXO_PAI_TRANSIT, 30                                                                                        )
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.prefixos_30 = disp

        if st.session_state.get('prefixos_30'):
            disp = st.session_state.prefixos_30
            if disp:
                st.success(f"✅ {len(disp)} prefixos /30 disponiveis")
                for i, p in enumerate(disp[:20], 1):
                    st.write(f"{i}. {p}")
                if len(disp) > 20:
                    st.caption(f"... e mais {len(disp) - 20}")
                pref_sel = st.selectbox("Prefixo:", disp[:50], key="pref_30_sel"                                                                                        )
                rede = pref_sel.split('/')[0]
                p    = rede.split('.')
                ip1  = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+1}"
                ip2  = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+2}"
                st.info(f"ℹ️ IPs: **{ip1}** e **{ip2}**")
                if st.button("✅ Alocar", type="primary", key="btn_alocar_30"):
                    with st.spinner("Alocando..."):
                        pref, erro = alocar_prefixo(pref_sel, tenant['id'])
                    if erro:
                        st.error(f"❌ {erro}")
                    else:
                        st.session_state.prefixo_30_alocado = {'id': pref.id, 'p                                                                                        refixo': str(pref.prefix)}
                        st.success("✅ Alocado!")
                        st.balloons()
                        st.rerun()
            else:
                st.warning("⚠️ Nenhum prefixo /30 disponivel")

# ============================================================================
# ETAPA 7: AWX - PROVISIONAR
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='background: white; border: 1.5px solid #e2e8f0; border-radius: 14px;
            padding: 20px 28px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(                                                                                        0,0,0,0.04);'>
    <div style='display:flex; align-items:center; gap:12px;'>
        <div style='width:40px; height:40px; border-radius:10px;
                    background:linear-gradient(135deg,#dbeafe,#bfdbfe);
                    display:flex; align-items:center; justify-content:center; fo                                                                                        nt-size:1.3rem;'>
            🚀
        </div>
        <div>
            <div style='font-size: 1.15rem; font-weight: 800; color: #1e3a5f;'>P                                                                                        rovisionar AWX</div>
            <div style='font-size: 0.82rem; color: #64748b; margin-top: 2px;'>
                Configure e dispare o Job Template com as variaveis coletadas.
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tenant    = st.session_state.tenant_criado
vlan_int  = st.session_state.vlan_internal_alocada
vlan_tran = st.session_state.vlan_transit_alocada
pref_24   = st.session_state.prefixo_24_alocado
pref_30   = st.session_state.prefixo_30_alocado
vrf       = st.session_state.vrf_criada

if not all([tenant, vlan_int, vlan_tran, pref_24, pref_30]):
    st.warning("⚠️ Complete todas as etapas anteriores para provisionar")
else:
    terceiro = int(str(vlan_int['vid'])[-2:]) if vlan_int['vid'] >= 100 else vla                                                                                        n_int['vid']
    ip_int   = st.text_input("IP SVI Internal:", value=f"10.101.{terceiro}.254")

    rede = pref_30['prefixo'].split('/')[0]
    p    = rede.split('.')
    ip1  = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+1}"
    ip2  = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+2}"

    uso     = st.radio("IPs /30:", [f"{ip1} (SW) | {ip2} (FW)", f"{ip1} (FW) | {                                                                                        ip2} (SW)"])
    ip_tran = ip1 if "SW" in uso.split("|")[0] else ip2
    ip_fw   = ip2 if ip_tran == ip1 else ip1

    vrf_name = vrf['nome'] if vrf else f"VRF_{tenant['slug'].upper()}"

    extra_vars = {
        "cliente_name":                str(tenant['slug'].upper()),
        "vlan_id_internal":            int(vlan_int['vid']),
        "vlan_id_internal_name":       str(vlan_int['nome']),
        "vlan_id_internal_l3_ip_addr": str(ip_int),
        "vlan_id_transit":             int(vlan_tran['vid']),
        "vlan_id_transit_name":        str(vlan_tran['nome']),
        "vlan_id_transit_l3_ipaddr":   str(ip_tran),
        "vrf_name":                    str(vrf_name),
        "vrf_next_hop":                str(ip_fw),
        "vrf_attributes":              str(f"1:{vlan_int['vid']}"),
        "vrf_routetarget_import":      str(VRF_ROUTETARGET_IMPORT),
        "bgp_asn":                     str(BGP_ASN),
        "route_policy":                str(ROUTE_POLICY),
    }

    st.subheader("📋 Variaveis AWX")
    st.code(f"""cliente_name: {extra_vars['cliente_name']}
vlan_id_internal: {extra_vars['vlan_id_internal']}
vlan_id_transit: {extra_vars['vlan_id_transit']}
vrf_name: {extra_vars['vrf_name']}
vrf_next_hop: {extra_vars['vrf_next_hop']}""", language="yaml")

    st.markdown("---")

    templates, err = listar_job_templates()
    if err:
        st.error(f"❌ {err}")
    elif templates:
        temp_sel = st.selectbox("Job Template:", [f"{t['name']} (ID: {t['id']})"                                                                                         for t in templates])
        temp_id  = int(temp_sel.split("ID: ")[1].rstrip(")"))

        if st.button("🚀 PROVISIONAR", type="primary", use_container_width=True)                                                                                        :
            job_id, url, erro = disparar_job_template(temp_id, extra_vars)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.success(f"✅ Job #{job_id} iniciado!")
                st.markdown(f"[🔗 Ver no AWX]({url})")

                status_container = st.empty()
                progresso_bar    = st.progress(0)

                for i in range(30):
                    status, _ = verificar_status_job(job_id)
                    progresso_bar.progress(min((i + 1) * 3, 100))

                    if status == "successful":
                        status_container.success("✅ Concluido!")
                        st.balloons()
                        break
                    elif status in ["failed", "error"]:
                        status_container.error(f"❌ Falhou: {status}")
                        break
                    elif status == "canceled":
                        status_container.warning("⚠️ Cancelado")
                        break
                    else:
                        status_container.info(f"⏳ {status.upper() if status els                                                                                        e 'AGUARDANDO'}")
                        time.sleep(2)
    else:
        st.warning("⚠️ Nenhum Job Template disponivel")

# ============================================================================
# RODAPE
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 12px 0;'>
    <span style='color: #94a3b8; font-size: 0.82rem;'>
        Portal NetBox + AWX &nbsp;•&nbsp; Python + Streamlit
    </span>
</div>
""", unsafe_allow_html=True)