from __future__ import annotations

from .types import BuiltinToolDef

from .agent_profile_upsert_section import run as _agent_profile_upsert_section_run
from .agent_profile_upsert_section import spec as _agent_profile_upsert_section_spec
from .agent_spec_delete import run as _agent_spec_delete_run
from .agent_spec_delete import spec as _agent_spec_delete_spec
from .agent_spec_write import run as _agent_spec_write_run
from .agent_spec_write import spec as _agent_spec_write_spec
from .file_edit import run as _file_edit_run
from .file_edit import spec as _file_edit_spec
from .file_list import run as _file_list_run
from .file_list import spec as _file_list_spec
from .file_read import run as _file_read_run
from .file_read import spec as _file_read_spec
from .file_write import run as _file_write_run
from .file_write import spec as _file_write_spec
from .project_code_list import run as _project_code_list_run
from .project_code_list import spec as _project_code_list_spec
from .project_code_read import run as _project_code_read_run
from .project_code_read import spec as _project_code_read_spec
from .project_command_run import run as _project_command_run_run
from .project_command_run import spec as _project_command_run_spec
from .project_deploy_run import run as _project_deploy_run_run
from .project_deploy_run import spec as _project_deploy_run_spec
from .user_profile_write import run as _user_profile_write_run
from .user_profile_write import spec as _user_profile_write_spec
from .worker_file_list import run as _worker_file_list_run
from .worker_file_list import spec as _worker_file_list_spec
from .worker_file_read import run as _worker_file_read_run
from .worker_file_read import spec as _worker_file_read_spec
from .worker_file_write import run as _worker_file_write_run
from .worker_file_write import spec as _worker_file_write_spec


BUILTIN_TOOL_DEFS: dict[str, BuiltinToolDef] = {
    "file_list": BuiltinToolDef(spec=_file_list_spec(), handler=_file_list_run),
    "file_read": BuiltinToolDef(spec=_file_read_spec(), handler=_file_read_run),
    "file_write": BuiltinToolDef(spec=_file_write_spec(), handler=_file_write_run),
    "file_edit": BuiltinToolDef(spec=_file_edit_spec(), handler=_file_edit_run),
    "project_code_list": BuiltinToolDef(spec=_project_code_list_spec(), handler=_project_code_list_run),
    "project_code_read": BuiltinToolDef(spec=_project_code_read_spec(), handler=_project_code_read_run),
    "worker_file_list": BuiltinToolDef(spec=_worker_file_list_spec(), handler=_worker_file_list_run),
    "worker_file_read": BuiltinToolDef(spec=_worker_file_read_spec(), handler=_worker_file_read_run),
    "worker_file_write": BuiltinToolDef(spec=_worker_file_write_spec(), handler=_worker_file_write_run),
    "user_profile_write": BuiltinToolDef(spec=_user_profile_write_spec(), handler=_user_profile_write_run),
    "agent_spec_write": BuiltinToolDef(spec=_agent_spec_write_spec(), handler=_agent_spec_write_run),
    "agent_spec_delete": BuiltinToolDef(spec=_agent_spec_delete_spec(), handler=_agent_spec_delete_run),
    "agent_profile_upsert_section": BuiltinToolDef(
        spec=_agent_profile_upsert_section_spec(), handler=_agent_profile_upsert_section_run
    ),
    "project_command_run": BuiltinToolDef(spec=_project_command_run_spec(), handler=_project_command_run_run),
    "project_deploy_run": BuiltinToolDef(spec=_project_deploy_run_spec(), handler=_project_deploy_run_run),
}
