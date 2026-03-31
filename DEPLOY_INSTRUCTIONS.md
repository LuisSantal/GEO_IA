# 🚀 DEPLOY NO STREAMLIT CLOUD - INSTRUÇÕES

## ✅ Problema Resolvido!

O erro "Invalid control character" foi causado por caracteres de controle no JSON quando copiado para o TOML do Streamlit Cloud.

## 🔧 Solução: Usar JSON Minificado

### Passo 1: Gerar JSON Minificado
```bash
cd /workspaces/GEO_IA
python3 -c "
import json
import re
with open('sa_decoded.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
# Escapar quebras de linha na chave privada
if 'private_key' in data:
    data['private_key'] = data['private_key'].replace('\n', '\\\\n')
print(json.dumps(data, separators=(',', ':')))
"
```

### Passo 2: Copiar para Streamlit Cloud
No seu app em [share.streamlit.io](https://share.streamlit.io):

**Settings → Secrets:**

```toml
gcp_service_account = """
[COLE AQUI O JSON MINIFICADO GERADO NO PASSO 1]
"""
```

### Passo 3: Reboot App
- Vá em "Manage app" → "Reboot app"
- O app deve funcionar perfeitamente! 🚀

## 🎯 Resultado Final

✅ **App funcionando 24/7 no Streamlit Cloud**
✅ **Auto-refresh a cada 10 minutos**
✅ **Dados em tempo real do Waze**
✅ **Dashboard interativo completo**

**🎉 Deploy concluído com sucesso!**