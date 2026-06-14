"""account_manager 单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 把 scripts/ 加入路径，使 account_manager 可导入
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import account_manager


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    """将配置目录重定向到临时目录。"""
    monkeypatch.setattr(account_manager, "_CONFIG_DIR", tmp_path / ".xhs")
    monkeypatch.setattr(
        account_manager, "_ACCOUNTS_FILE", tmp_path / ".xhs" / "accounts.json"
    )


def test_add_account_assigns_port():
    """首个命名账号应分配端口 9223。"""
    account_manager.add_account("work", "工作号")
    port = account_manager.get_account_port("work")
    assert port == 9223


def test_second_account_gets_next_port():
    """第二个账号应分配端口 9224。"""
    account_manager.add_account("work")
    account_manager.add_account("personal")
    assert account_manager.get_account_port("personal") == 9224


def test_get_profile_dir_public():
    """get_profile_dir 应返回正确路径。"""
    account_manager.add_account("work")
    profile = account_manager.get_profile_dir("work")
    assert "work" in profile
    assert "chrome-profile" in profile


def test_get_account_port_unknown_raises():
    """不存在的账号应抛出 ValueError。"""
    with pytest.raises(ValueError, match="不存在"):
        account_manager.get_account_port("ghost")


def test_list_accounts_includes_port():
    """list_accounts 返回结果中应包含 port 字段。"""
    account_manager.add_account("work", "工作")
    accounts = account_manager.list_accounts()
    assert len(accounts) == 1
    assert accounts[0]["port"] == 9223


def test_set_account_card_config():
    """账号可绑定默认卡片配置。"""
    account_manager.add_account("zhanghe", "张和")
    card_config = account_manager.set_account_card_config(
        "zhanghe",
        style="unified-claude",
        chapter_label="张和 AI 产品实战派",
        cover_template="default",
        cover_style="template",
    )
    assert card_config == {
        "style": "unified-claude",
        "chapter_label": "张和 AI 产品实战派",
        "cover_template": "default",
        "cover_style": "template",
    }
    accounts = account_manager.list_accounts()
    assert accounts[0]["card_config"]["style"] == "unified-claude"


def test_set_account_card_config_clear_removes_config():
    """卡片配置可以清空。"""
    account_manager.add_account("zhanghe")
    account_manager.set_account_card_config("zhanghe", style="unified-claude")
    card_config = account_manager.set_account_card_config("zhanghe", clear=True)
    assert card_config == {}
    assert account_manager.get_account_card_config("zhanghe") == {}


def test_set_account_card_config_rejects_bad_cover_template():
    """封面模板字段应校验枚举值。"""
    account_manager.add_account("zhanghe")
    with pytest.raises(ValueError, match="cover_template"):
        account_manager.set_account_card_config("zhanghe", cover_template="weird")
