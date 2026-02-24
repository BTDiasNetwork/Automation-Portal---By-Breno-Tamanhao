import streamlit as st
import pynetbox
import requests
import os
from dotenv import load_dotenv
import urllib3
import time
import hashlib


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

st.set_page_config(
    page_title="Portal NetBox + AWX",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# AUTENTICAÇÃO
# ============================================================================


def hash_senha(senha):
    """Gera hash SHA256 da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

# Usuários cadastrados
USUARIOS = {
    'admin': {
        'senha_hash': hash_senha('ish@init123!@#'),
        'nome': 'Administrador',
        'email': 'admin@empresa.com'
    },
'ish02090': {
        'senha_hash': hash_senha('ish@init'),
        'nome': 'Breno Tamanhao Dias',
        'email': 'breno.dias@ish.com.br'
    }
}

def verificar_login(usuario, senha):
    """Verifica credenciais do usuário"""
    if usuario in USUARIOS:
        senha_hash = hash_senha(senha)
        if USUARIOS[usuario]['senha_hash'] == senha_hash:
            return True, USUARIOS[usuario]
    return False, None

# Inicializar session state
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'usuario_info' not in st.session_state:
    st.session_state.usuario_info = None

# ============================================================================
# TELA DE LOGIN
# ============================================================================

if not st.session_state.autenticado:
    st.markdown("""
    <style>
        .login-header {
            text-align: center;
            color: #3b82f6;
            margin-bottom: 30px;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<h1 class='login-header'>🔐 Login</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #64748b;'>Portal NetBox + AWX</h3>", unsafe_allow_html=True)
        st.markdown("---")

        with st.form("login_form"):
            usuario = st.text_input("👤 Usuário", placeholder="Digite seu login")
            senha = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha")

            submit = st.form_submit_button("🚀 Entrar", use_container_width=True, type="primary")

            if submit:
                if usuario and senha:
                    sucesso, info_usuario = verificar_login(usuario, senha)

                    if sucesso:
                        st.session_state.autenticado = True
                        st.session_state.usuario_info = {
                            'usuario': usuario,
                            'nome': info_usuario['nome'],
                            'email': info_usuario['email']
                        }
                        st.success("✅ Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos")
                else:
                    st.warning("⚠️ Preencha usuário e senha")

        st.markdown("---")
        st.info("💡 Conecte com seu usuário do AD")

    st.stop()

# ============================================================================
# USUÁRIO AUTENTICADO - APLICAÇÃO PRINCIPAL
# ============================================================================

# CSS Moderno
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    h1 {
        background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    h2 {
        color: #3b82f6;
        font-weight: 700;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Configurações
NETBOX_URL = os.getenv("NETBOX_URL")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN")
AWX_URL = os.getenv("AWX_URL")
AWX_USER = os.getenv("AWX_USER")
AWX_PASSWORD = os.getenv("AWX_PASSWORD")

PREFIXO_PAI_INTERNAL = "10.101.0.0/16"
PREFIXO_PAI_TRANSIT = "100.64.0.0/23"

BGP_ASN = "65001"
ROUTE_POLICY = "RP_DENY-CGNAT_DC"
VRF_ROUTETARGET_IMPORT = "1:1900"

# Conexão NetBox
@st.cache_resource
def conectar_netbox():
    try:
        nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
        nb.http_session.verify = False
        _ = nb.version
        return nb, None
    except Exception as e:
        return None, str(e)

nb, erro = conectar_netbox()

# Funções NetBox
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
        filtro = {'vid__gte': vlan_inicio, 'vid__lte': vlan_fim}
        vlans_cadastradas = list(nb.ipam.vlans.filter(**filtro))
        vlans_usadas = {vlan.vid for vlan in vlans_cadastradas}
        todas_vlans = set(range(vlan_inicio, vlan_fim + 1))
        vlans_disponiveis = sorted(todas_vlans - vlans_usadas)
        return vlans_disponiveis, vlans_cadastradas, None
    except Exception as e:
        return None, None, str(e)

def alocar_vlan(vid, nome, tenant_id, descricao=""):
    try:
        dados = {'vid': vid, 'name': nome, 'tenant': tenant_id, 'status': 'active'}
        if descricao:
            dados['description'] = descricao
        return nb.ipam.vlans.create(**dados), None
    except Exception as e:
        return None, str(e)

def buscar_prefixos_disponiveis(prefixo_pai, mascara):
    try:
        prefix = nb.ipam.prefixes.get(prefix=prefixo_pai)
        if not prefix:
            return None, f"Prefixo {prefixo_pai} não encontrado"
        disponiveis = prefix.available_prefixes.list(prefix_length=mascara)
        return [str(p) for p in disponiveis], None
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

# Funções AWX
def listar_job_templates():
    try:
        from requests.auth import HTTPBasicAuth
        url = f"{AWX_URL}/api/v2/job_templates/"
        response = requests.get(url, auth=HTTPBasicAuth(AWX_USER, AWX_PASSWORD), verify=False, timeout=10)
        if response.status_code == 200:
            return response.json().get('results', []), None
        return None, f"Erro {response.status_code}"
    except Exception as e:
        return None, str(e)

def disparar_job_template(template_id, extra_vars):
    try:
        from requests.auth import HTTPBasicAuth
        url = f"{AWX_URL}/api/v2/job_templates/{template_id}/launch/"
        response = requests.post(url, auth=HTTPBasicAuth(AWX_USER, AWX_PASSWORD), json={"extra_vars": extra_vars}, verify=False)
        if response.status_code in [200, 201]:
            job_data = response.json()
            return job_data.get('id'), f"{AWX_URL}/#/jobs/playbook/{job_data.get('id')}", None
        try:
            error_detail = response.json()
            return None, None, f"Erro {response.status_code}: {error_detail}"
        except:
            return None, None, f"Erro {response.status_code}: {response.text}"
    except Exception as e:
        return None, None, str(e)

def verificar_status_job(job_id):
    try:
        from requests.auth import HTTPBasicAuth
        url = f"{AWX_URL}/api/v2/jobs/{job_id}/"
        response = requests.get(url, auth=HTTPBasicAuth(AWX_USER, AWX_PASSWORD), verify=False)
        if response.status_code == 200:
            return response.json().get('status'), None
        return None, f"Erro {response.status_code}"
    except Exception as e:
        return None, str(e)

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### 👤 Sessão Ativa")
    st.write(f"**Nome:** {st.session_state.usuario_info['nome']}")
    st.write(f"**Usuário:** {st.session_state.usuario_info['usuario']}")
    st.markdown("---")

    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_info = None
        st.rerun()

    st.markdown("---")

# Interface
st.markdown("<h1 style='text-align: center;'> Portal de Automação NetBox + AWX</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; font-size: 18px; color: #64748b;'>Bem-vindo, {st.session_state.usuario_info['nome']}!</p>", unsafe_allow_html=True)
st.markdown("---")

if erro:
    st.error(f"❌ NetBox: {erro}")
    st.stop()

# Status Cards
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px; border-radius: 10px; color: white;'>
        <h3 style='margin: 0; color: white;'>🌐 NetBox</h3>
        <p style='margin: 5px 0; font-size: 14px;'>Conectado v{nb.version}</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    try:
        templates, _ = listar_job_templates()
        if templates:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 20px; border-radius: 10px; color: white;'>
                <h3 style='margin: 0; color: white;'>⚙️ AWX</h3>
                <p style='margin: 5px 0; font-size: 14px;'>{len(templates)} Job Templates</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ AWX não configurado")
    except:
        st.warning("⚠️ AWX não configurado")

st.markdown("---")

# Session State
if 'tenant_criado' not in st.session_state:
    st.session_state.tenant_criado = None
if 'vrf_criada' not in st.session_state:
    st.session_state.vrf_criada = None
if 'vlan_internal_alocada' not in st.session_state:
    st.session_state.vlan_internal_alocada = None
if 'vlan_transit_alocada' not in st.session_state:
    st.session_state.vlan_transit_alocada = None
if 'prefixo_24_alocado' not in st.session_state:
    st.session_state.prefixo_24_alocado = None
if 'prefixo_30_alocado' not in st.session_state:
    st.session_state.prefixo_30_alocado = None

# Progresso
etapas_completas = sum([
    st.session_state.tenant_criado is not None,
    st.session_state.vrf_criada is not None,
    st.session_state.vlan_internal_alocada is not None,
    st.session_state.vlan_transit_alocada is not None,
    st.session_state.prefixo_24_alocado is not None,
    st.session_state.prefixo_30_alocado is not None
])

st.progress(etapas_completas / 6)
st.write(f"**Progresso:** {etapas_completas}/6 etapas concluídas")
st.markdown("---")

# ETAPA 1: TENANT
with st.expander("1️⃣ Criar Tenant", expanded=(st.session_state.tenant_criado is None)):
    if st.session_state.tenant_criado:
        st.success(f"✅ Tenant: **{st.session_state.tenant_criado['nome']}**")
        if st.button("🔄 Resetar", key="reset_tenant"):
            for key in ['tenant_criado', 'vrf_criada', 'vlan_internal_alocada', 'vlan_transit_alocada', 'prefixo_24_alocado', 'prefixo_30_alocado']:
                st.session_state[key] = None
            st.rerun()
    else:
        groups, _ = listar_tenant_groups()
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome:", placeholder="Empresa ABC", key="nome_tenant")
            slug = st.text_input("Slug:", placeholder="empresa-abc", key="slug_tenant")
        with col2:
            if groups:
                group_opt = ["Nenhum"] + [f"{g.name} (ID: {g.id})" for g in groups]
                group_sel = st.selectbox("Grupo:", group_opt, key="group_tenant")
                group_id = None if group_sel == "Nenhum" else int(group_sel.split("ID: ")[1].rstrip(")"))
            else:
                group_id = None
            desc = st.text_area("Descrição:", key="desc_tenant")

        if st.button("✅ Criar Tenant", type="primary", key="btn_criar_tenant"):
            if nome and slug:
                tenant, erro = criar_tenant(nome, slug, group_id, desc)
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.tenant_criado = {'id': tenant.id, 'nome': tenant.name, 'slug': tenant.slug}
                    st.success("✅ Criado!")
                    st.balloons()
                    st.rerun()
            else:
                st.error("❌ Preencha nome e slug")

# ETAPA 2: VRF
with st.expander("2️⃣ Criar VRF", expanded=(st.session_state.tenant_criado is not None and st.session_state.vrf_criada is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.vrf_criada:
        st.success(f"✅ VRF: **{st.session_state.vrf_criada['nome']}**")
    else:
        tenant = st.session_state.tenant_criado
        col1, col2 = st.columns(2)
        with col1:
            nome_vrf = st.text_input("Nome VRF:", value=f"VRF_{tenant['slug'].upper()}", key="nome_vrf")
            rd = st.text_input("RD:", placeholder="65000:100", key="rd_vrf")
        with col2:
            desc_vrf = st.text_area("Descrição:", key="desc_vrf")

        if st.button("✅ Criar VRF", type="primary", key="btn_criar_vrf"):
            if nome_vrf and rd:
                vrf, erro = criar_vrf(nome_vrf, rd, tenant['id'], desc_vrf)
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.vrf_criada = {'id': vrf.id, 'nome': vrf.name, 'rd': vrf.rd}
                    st.success("✅ Criada!")
                    st.balloons()
                    st.rerun()
            else:
                st.error("❌ Preencha todos os campos")

# ETAPA 3: VLAN INTERNAL
with st.expander("3️⃣ VLAN Internal", expanded=(st.session_state.vrf_criada is not None and st.session_state.vlan_internal_alocada is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.vlan_internal_alocada:
        v = st.session_state.vlan_internal_alocada
        st.success(f"✅ VLAN {v['vid']} - {v['nome']}")
    else:
        tenant = st.session_state.tenant_criado
        col1, col2, col3 = st.columns(3)
        with col1:
            inicio = st.number_input("Início:", 1, 4094, 100, key="vlan_int_inicio")
        with col2:
            fim = st.number_input("Fim:", 1, 4094, 500, key="vlan_int_fim")
        with col3:
            st.write("")
            st.write("")
            buscar = st.button("🔎 Buscar", key="btn_buscar_vlan_int")

        if buscar:
            disp, cad, erro = buscar_vlans_disponiveis(inicio, fim)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.vlans_int_disp = disp

        if 'vlans_int_disp' in st.session_state and st.session_state.vlans_int_disp:
            disp = st.session_state.vlans_int_disp
            st.success(f"✅ {len(disp)} VLANs disponíveis")
            st.write(', '.join(map(str, disp[:30])))

            vlan_sel = st.selectbox("VLAN:", disp[:50], key="vlan_int_sel")
            nome_vlan = st.text_input("Nome:", value=f"VLAN_{tenant['slug'].upper()}_{vlan_sel}_INT", key="vlan_int_nome")

            if st.button("✅ Alocar", type="primary", key="btn_alocar_vlan_int"):
                vlan, erro = alocar_vlan(vlan_sel, nome_vlan, tenant['id'])
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.vlan_internal_alocada = {'id': vlan.id, 'vid': vlan.vid, 'nome': vlan.name}
                    st.success("✅ Alocada!")
                    st.balloons()
                    st.rerun()

# ETAPA 4: VLAN TRANSIT
with st.expander("4️⃣ VLAN Transit", expanded=(st.session_state.vlan_internal_alocada is not None and st.session_state.vlan_transit_alocada is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.vlan_transit_alocada:
        v = st.session_state.vlan_transit_alocada
        st.success(f"✅ VLAN {v['vid']} - {v['nome']}")
    else:
        tenant = st.session_state.tenant_criado
        col1, col2, col3 = st.columns(3)
        with col1:
            inicio = st.number_input("Início:", 1, 4094, 800, key="vlan_tran_inicio")
        with col2:
            fim = st.number_input("Fim:", 1, 4094, 900, key="vlan_tran_fim")
        with col3:
            st.write("")
            st.write("")
            buscar = st.button("🔎 Buscar", key="btn_buscar_vlan_tran")

        if buscar:
            disp, cad, erro = buscar_vlans_disponiveis(inicio, fim)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.vlans_tran_disp = disp

        if 'vlans_tran_disp' in st.session_state and st.session_state.vlans_tran_disp:
            disp = st.session_state.vlans_tran_disp
            st.success(f"✅ {len(disp)} VLANs disponíveis")
            st.write(', '.join(map(str, disp[:30])))

            vlan_sel = st.selectbox("VLAN:", disp[:50], key="vlan_tran_sel")
            nome_vlan = st.text_input("Nome:", value=f"VLAN_{tenant['slug'].upper()}_{vlan_sel}_TRAN", key="vlan_tran_nome")

            if st.button("✅ Alocar", type="primary", key="btn_alocar_vlan_tran"):
                vlan, erro = alocar_vlan(vlan_sel, nome_vlan, tenant['id'])
                if erro:
                    st.error(f"❌ {erro}")
                else:
                    st.session_state.vlan_transit_alocada = {'id': vlan.id, 'vid': vlan.vid, 'nome': vlan.name}
                    st.success("✅ Alocada!")
                    st.balloons()
                    st.rerun()

# ETAPA 5: PREFIXO /24
with st.expander("5️⃣ Prefixo /24", expanded=(st.session_state.vlan_transit_alocada is not None and st.session_state.prefixo_24_alocado is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.prefixo_24_alocado:
        st.success(f"✅ {st.session_state.prefixo_24_alocado['prefixo']}")
    else:
        tenant = st.session_state.tenant_criado
        st.info(f"🔍 Prefixo Pai: **{PREFIXO_PAI_INTERNAL}**")

        if st.button("🔎 Buscar /24", key="btn_buscar_24"):
            with st.spinner("Buscando..."):
                disp, erro = buscar_prefixos_disponiveis(PREFIXO_PAI_INTERNAL, 24)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.prefixos_24 = disp

        if 'prefixos_24' in st.session_state and st.session_state.prefixos_24:
            disp = st.session_state.prefixos_24
            if disp:
                st.success(f"✅ {len(disp)} prefixos disponíveis")
                for i, p in enumerate(disp[:20], 1):
                    st.write(f"{i}. {p}")
                if len(disp) > 20:
                    st.caption(f"... e mais {len(disp) - 20}")

                pref_sel = st.selectbox("Prefixo:", disp[:50], key="pref_24_sel")

                if st.button("✅ Alocar", type="primary", key="btn_alocar_24"):
                    with st.spinner("Alocando..."):
                        pref, erro = alocar_prefixo(pref_sel, tenant['id'])
                    if erro:
                        st.error(f"❌ {erro}")
                    else:
                        st.session_state.prefixo_24_alocado = {'id': pref.id, 'prefixo': str(pref.prefix)}
                        st.success("✅ Alocado!")
                        st.balloons()
                        st.rerun()
            else:
                st.warning("⚠️ Nenhum prefixo disponível")

# ETAPA 6: PREFIXO /30
with st.expander("6️⃣ Prefixo /30", expanded=(st.session_state.prefixo_24_alocado is not None and st.session_state.prefixo_30_alocado is None)):
    if not st.session_state.tenant_criado:
        st.warning("⚠️ Crie um tenant primeiro")
    elif st.session_state.prefixo_30_alocado:
        st.success(f"✅ {st.session_state.prefixo_30_alocado['prefixo']}")
    else:
        tenant = st.session_state.tenant_criado
        st.info(f"🔍 Prefixo Pai: **{PREFIXO_PAI_TRANSIT}**")

        if st.button("🔎 Buscar /30", key="btn_buscar_30"):
            with st.spinner("Buscando..."):
                disp, erro = buscar_prefixos_disponiveis(PREFIXO_PAI_TRANSIT, 30)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.session_state.prefixos_30 = disp

        if 'prefixos_30' in st.session_state and st.session_state.prefixos_30:
            disp = st.session_state.prefixos_30
            if disp:
                st.success(f"✅ {len(disp)} prefixos disponíveis")
                for i, p in enumerate(disp[:20], 1):
                    st.write(f"{i}. {p}")
                if len(disp) > 20:
                    st.caption(f"... e mais {len(disp) - 20}")

                pref_sel = st.selectbox("Prefixo:", disp[:50], key="pref_30_sel")

                rede = pref_sel.split('/')[0]
                p = rede.split('.')
                ip1 = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+1}"
                ip2 = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+2}"
                st.info(f"📌 IPs: **{ip1}** e **{ip2}**")

                if st.button("✅ Alocar", type="primary", key="btn_alocar_30"):
                    with st.spinner("Alocando..."):
                        pref, erro = alocar_prefixo(pref_sel, tenant['id'])
                    if erro:
                        st.error(f"❌ {erro}")
                    else:
                        st.session_state.prefixo_30_alocado = {'id': pref.id, 'prefixo': str(pref.prefix)}
                        st.success("✅ Alocado!")
                        st.balloons()
                        st.rerun()
            else:
                st.warning("⚠️ Nenhum prefixo disponível")

# ETAPA 7: AWX
st.markdown("---")
st.header("🚀 Provisionar AWX")

tenant = st.session_state.tenant_criado
vlan_int = st.session_state.vlan_internal_alocada
vlan_tran = st.session_state.vlan_transit_alocada
pref_24 = st.session_state.prefixo_24_alocado
pref_30 = st.session_state.prefixo_30_alocado
vrf = st.session_state.vrf_criada

if not all([tenant, vlan_int, vlan_tran, pref_24, pref_30]):
    st.warning("⚠️ Complete todas as etapas anteriores")
else:
    # Calcular IPs
    terceiro = int(str(vlan_int['vid'])[-2:]) if vlan_int['vid'] >= 100 else vlan_int['vid']
    ip_int = st.text_input("IP SVI Internal:", value=f"10.101.{terceiro}.254")

    rede = pref_30['prefixo'].split('/')[0]
    p = rede.split('.')
    ip1 = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+1}"
    ip2 = f"{p[0]}.{p[1]}.{p[2]}.{int(p[3])+2}"

    uso = st.radio("IPs /30:", [f"{ip1} (SW) | {ip2} (FW)", f"{ip1} (FW) | {ip2} (SW)"])
    ip_tran = ip1 if "SW" in uso.split("|")[0] else ip2
    ip_fw = ip2 if ip_tran == ip1 else ip1

    # Variáveis AWX
    vrf_name = vrf['nome'] if vrf else f"VRF_{tenant['slug'].upper()}"

    extra_vars = {
        "cliente_name": str(tenant['slug'].upper()),
        "vlan_id_internal": int(vlan_int['vid']),
        "vlan_id_internal_name": str(vlan_int['nome']),
        "vlan_id_internal_l3_ip_addr": str(ip_int),
        "vlan_id_transit": int(vlan_tran['vid']),
        "vlan_id_transit_name": str(vlan_tran['nome']),
        "vlan_id_transit_l3_ipaddr": str(ip_tran),
        "vrf_name": str(vrf_name),
        "vrf_next_hop": str(ip_fw),
        "vrf_attributes": str(f"1:{vlan_int['vid']}"),
        "vrf_routetarget_import": str(VRF_ROUTETARGET_IMPORT),
        "bgp_asn": str(BGP_ASN),
        "route_policy": str(ROUTE_POLICY)
    }

    st.subheader("📋 Variáveis AWX")
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
        temp_sel = st.selectbox("Job Template:", [f"{t['name']} (ID: {t['id']})" for t in templates])
        temp_id = int(temp_sel.split("ID: ")[1].rstrip(")"))

        if st.button("🚀 PROVISIONAR", type="primary", use_container_width=True):
            job_id, url, erro = disparar_job_template(temp_id, extra_vars)
            if erro:
                st.error(f"❌ {erro}")
            else:
                st.success(f"✅ Job #{job_id}")
                st.markdown(f"[Ver no AWX]({url})")

                status_container = st.empty()
                progresso = st.progress(0)

                for i in range(30):
                    status, _ = verificar_status_job(job_id)
                    progresso.progress(min((i + 1) * 3, 100))

                    if status == "successful":
                        status_container.success("✅ Concluído!")
                        st.balloons()
                        break
                    elif status in ["failed", "error"]:
                        status_container.error(f"❌ Falhou: {status}")
                        break
                    elif status == "canceled":
                        status_container.warning("⚠️ Cancelado")
                        break
                    else:
                        status_container.info(f"🔄 {status.upper()}")
                        time.sleep(2)
    else:
        st.warning("⚠️ Nenhum Job Template")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748b;'>Portal NetBox + AWX | Python + Streamlit</p>", unsafe_allow_html=True)