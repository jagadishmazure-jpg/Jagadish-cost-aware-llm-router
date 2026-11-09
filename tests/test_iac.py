import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TF = (ROOT / "infra/terraform/main.tf").read_text()
BICEP = (ROOT / "infra/bicep/main.bicep").read_text()
DEPLOY = (ROOT / ".github/workflows/deploy.yml").read_text()

# Azure resource types each stack creates (Terraform resource -> ARM type)
TF_TO_ARM = {
    "azurerm_log_analytics_workspace": "Microsoft.OperationalInsights/workspaces",
    "azurerm_application_insights": "Microsoft.Insights/components",
    "azurerm_storage_account": "Microsoft.Storage/storageAccounts",
    "azurerm_key_vault": "Microsoft.KeyVault/vaults",
    "azurerm_monitor_diagnostic_setting": "Microsoft.Insights/diagnosticSettings",
}


def tf_types():
    out = []
    for kind in re.findall(r'^resource "(\w+)"', TF, re.M):
        if kind in TF_TO_ARM:
            out.append(TF_TO_ARM[kind])
    out += re.findall(r'type\s*=\s*"([\w./]+)@', TF)
    return sorted(out)


def bicep_types():
    return sorted(re.findall(r"^resource \w+ '([\w./]+)@", BICEP, re.M))


def test_terraform_and_bicep_create_the_same_resources():
    assert tf_types() == bicep_types()


def test_same_api_versions_for_ml_resources():
    for t in ("workspaces", "workspaces/onlineEndpoints"):
        tfv = re.search(rf'MachineLearningServices/{t}@([\w-]+)"', TF).group(1)
        bv = re.search(rf"MachineLearningServices/{t}@([\w-]+)'", BICEP).group(1)
        assert tfv == bv


def test_endpoint_uses_entra_tokens_in_both():
    assert 'authMode            = "AADToken"' in TF and "authMode: 'AADToken'" in BICEP


def test_storage_is_entra_only_in_both():
    assert "shared_access_key_enabled       = false" in TF and "allowSharedKeyAccess: false" in BICEP
    assert TF.count('systemDatastoresAuthMode = "identity"') == 1 and "systemDatastoresAuthMode: 'identity'" in BICEP


def test_key_vault_rbac_and_purge_protection_in_both():
    assert "rbac_authorization_enabled = true" in TF and "enableRbacAuthorization: true" in BICEP
    assert "purge_protection_enabled   = true" in TF and "enablePurgeProtection: true" in BICEP


def test_deploy_workflow_is_gated_and_manual():
    assert re.search(r"^on:\n  workflow_dispatch:", DEPLOY, re.M) and "push:" not in DEPLOY
    jobs = re.findall(r"^  ([\w-]+):\n", DEPLOY.split("\njobs:\n", 1)[1], re.M)
    for job in jobs:
        if job == "preflight":
            continue
        block = DEPLOY.split(f"\n  {job}:\n", 1)[1].split("\n  \n", 1)[0]
        assert "if: vars.DEPLOY_ENABLED == 'true'" in block, job


def test_deploy_uses_oidc_not_secrets():
    assert "id-token: write" in DEPLOY and "secrets." not in DEPLOY


def test_all_actions_pinned_to_full_sha():
    for wf in (ROOT / ".github/workflows").glob("*.yml"):
        for ref in re.findall(r"uses:\s*[\w.-]+/[\w./-]+@(\S+)", wf.read_text()):
            assert re.fullmatch(r"[0-9a-f]{40}", ref), (wf.name, ref)
