
// this file is generated — do not edit it


/// <reference types="@sveltejs/kit" />

/**
 * Environment variables [loaded by Vite](https://vitejs.dev/guide/env-and-mode.html#env-files) from `.env` files and `process.env`. Like [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), this module cannot be imported into client-side code. This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured).
 * 
 * _Unlike_ [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), the values exported from this module are statically injected into your bundle at build time, enabling optimisations like dead code elimination.
 * 
 * ```ts
 * import { API_KEY } from '$env/static/private';
 * ```
 * 
 * Note that all environment variables referenced in your code should be declared (for example in an `.env` file), even if they don't have a value until the app is deployed:
 * 
 * ```
 * MY_FEATURE_FLAG=""
 * ```
 * 
 * You can override `.env` values from the command line like so:
 * 
 * ```sh
 * MY_FEATURE_FLAG="enabled" npm run dev
 * ```
 */
declare module '$env/static/private' {
	export const SHELL: string;
	export const LSCOLORS: string;
	export const SESSION_MANAGER: string;
	export const WINDOWID: string;
	export const GHOSTTY_BIN_DIR: string;
	export const COLORTERM: string;
	export const _ZO_DOCTOR: string;
	export const TERM_PROGRAM_VERSION: string;
	export const GNOME_DESKTOP_SESSION_ID: string;
	export const QT_IM_MODULES: string;
	export const GNOME_KEYRING_CONTROL: string;
	export const LANGUAGE: string;
	export const NODE: string;
	export const npm_config_ignore_scripts: string;
	export const LC_ADDRESS: string;
	export const VSCODE_PROCESS_TITLE: string;
	export const LC_NAME: string;
	export const npm_config_argv: string;
	export const XMODIFIERS: string;
	export const npm_config_bin_links: string;
	export const DESKTOP_SESSION: string;
	export const LC_MONETARY: string;
	export const NO_AT_BRIDGE: string;
	export const CURSOR_EXTENSION_HOST_ROLE: string;
	export const GTK_MODULES: string;
	export const XDG_SEAT: string;
	export const PWD: string;
	export const npm_config_save_prefix: string;
	export const npm_package_devDependencies_vite: string;
	export const LOGNAME: string;
	export const XDG_SESSION_DESKTOP: string;
	export const XDG_SESSION_TYPE: string;
	export const VSCODE_ESM_ENTRYPOINT: string;
	export const npm_package_scripts_build: string;
	export const VSCODE_CODE_CACHE_PATH: string;
	export const _: string;
	export const XAUTHORITY: string;
	export const WINDOWPATH: string;
	export const MOTD_SHOWN: string;
	export const GDM_LANG: string;
	export const GHOSTTY_SHELL_FEATURES: string;
	export const HOME: string;
	export const USERNAME: string;
	export const npm_config_version_git_tag: string;
	export const LANG: string;
	export const LC_PAPER: string;
	export const LS_COLORS: string;
	export const XDG_CURRENT_DESKTOP: string;
	export const npm_config_init_license: string;
	export const npm_package_version: string;
	export const VSCODE_IPC_HOOK: string;
	export const npm_config_version_commit_hooks: string;
	export const FORCE_COLOR: string;
	export const VSCODE_CLI: string;
	export const npm_package_devDependencies__sveltejs_adapter_static: string;
	export const INIT_CWD: string;
	export const CHROME_DESKTOP: string;
	export const npm_package_scripts_preview: string;
	export const npm_lifecycle_script: string;
	export const CURSOR_AGENT: string;
	export const npm_config_version_tag_prefix: string;
	export const npm_package_devDependencies__sveltejs_vite_plugin_svelte: string;
	export const YARN_WRAP_OUTPUT: string;
	export const GHOSTTY_RESOURCES_DIR: string;
	export const XDG_SESSION_CLASS: string;
	export const TERM: string;
	export const TERMINFO: string;
	export const LC_IDENTIFICATION: string;
	export const npm_package_name: string;
	export const ZSH: string;
	export const npm_package_type: string;
	export const USER: string;
	export const EVERYSPHERE_RIPGREP_PATH: string;
	export const DISPLAY: string;
	export const npm_lifecycle_event: string;
	export const VSCODE_PID: string;
	export const SHLVL: string;
	export const npm_config_version_git_sign: string;
	export const npm_config_version_git_message: string;
	export const PAGER: string;
	export const LC_TELEPHONE: string;
	export const QT_IM_MODULE: string;
	export const LC_MEASUREMENT: string;
	export const VSCODE_CWD: string;
	export const XDG_VTNR: string;
	export const XDG_SESSION_ID: string;
	export const npm_config_user_agent: string;
	export const NO_COLOR: string;
	export const npm_execpath: string;
	export const VSCODE_CRASH_REPORTER_PROCESS_TYPE: string;
	export const XDG_RUNTIME_DIR: string;
	export const npm_config_strict_ssl: string;
	export const DEBUGINFOD_URLS: string;
	export const npm_package_scripts_dev: string;
	export const ELECTRON_NO_ATTACH_CONSOLE: string;
	export const GTK3_MODULES: string;
	export const GDK_BACKEND: string;
	export const npm_package_dependencies_svelte: string;
	export const PATH: string;
	export const GDMSESSION: string;
	export const npm_package_devDependencies__sveltejs_kit: string;
	export const CI: string;
	export const ORIGINAL_XDG_CURRENT_DESKTOP: string;
	export const DBUS_SESSION_BUS_ADDRESS: string;
	export const VSCODE_NLS_CONFIG: string;
	export const MAIL: string;
	export const npm_config_registry: string;
	export const npm_package_scripts_sync: string;
	export const npm_config_ignore_optional: string;
	export const npm_node_execpath: string;
	export const VSCODE_HANDLES_UNCAUGHT_ERRORS: string;
	export const OLDPWD: string;
	export const TERM_PROGRAM: string;
	export const CURSOR_TRACE_ID: string;
	export const npm_config_init_version: string;
	export const NODE_ENV: string;
}

/**
 * Similar to [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private), except that it only includes environment variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`), and can therefore safely be exposed to client-side code.
 * 
 * Values are replaced statically at build time.
 * 
 * ```ts
 * import { PUBLIC_BASE_URL } from '$env/static/public';
 * ```
 */
declare module '$env/static/public' {
	
}

/**
 * This module provides access to runtime environment variables, as defined by the platform you're running on. For example if you're using [`adapter-node`](https://github.com/sveltejs/kit/tree/main/packages/adapter-node) (or running [`vite preview`](https://svelte.dev/docs/kit/cli)), this is equivalent to `process.env`. This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured).
 * 
 * This module cannot be imported into client-side code.
 * 
 * ```ts
 * import { env } from '$env/dynamic/private';
 * console.log(env.DEPLOYMENT_SPECIFIC_VARIABLE);
 * ```
 * 
 * > [!NOTE] In `dev`, `$env/dynamic` always includes environment variables from `.env`. In `prod`, this behavior will depend on your adapter.
 */
declare module '$env/dynamic/private' {
	export const env: {
		SHELL: string;
		LSCOLORS: string;
		SESSION_MANAGER: string;
		WINDOWID: string;
		GHOSTTY_BIN_DIR: string;
		COLORTERM: string;
		_ZO_DOCTOR: string;
		TERM_PROGRAM_VERSION: string;
		GNOME_DESKTOP_SESSION_ID: string;
		QT_IM_MODULES: string;
		GNOME_KEYRING_CONTROL: string;
		LANGUAGE: string;
		NODE: string;
		npm_config_ignore_scripts: string;
		LC_ADDRESS: string;
		VSCODE_PROCESS_TITLE: string;
		LC_NAME: string;
		npm_config_argv: string;
		XMODIFIERS: string;
		npm_config_bin_links: string;
		DESKTOP_SESSION: string;
		LC_MONETARY: string;
		NO_AT_BRIDGE: string;
		CURSOR_EXTENSION_HOST_ROLE: string;
		GTK_MODULES: string;
		XDG_SEAT: string;
		PWD: string;
		npm_config_save_prefix: string;
		npm_package_devDependencies_vite: string;
		LOGNAME: string;
		XDG_SESSION_DESKTOP: string;
		XDG_SESSION_TYPE: string;
		VSCODE_ESM_ENTRYPOINT: string;
		npm_package_scripts_build: string;
		VSCODE_CODE_CACHE_PATH: string;
		_: string;
		XAUTHORITY: string;
		WINDOWPATH: string;
		MOTD_SHOWN: string;
		GDM_LANG: string;
		GHOSTTY_SHELL_FEATURES: string;
		HOME: string;
		USERNAME: string;
		npm_config_version_git_tag: string;
		LANG: string;
		LC_PAPER: string;
		LS_COLORS: string;
		XDG_CURRENT_DESKTOP: string;
		npm_config_init_license: string;
		npm_package_version: string;
		VSCODE_IPC_HOOK: string;
		npm_config_version_commit_hooks: string;
		FORCE_COLOR: string;
		VSCODE_CLI: string;
		npm_package_devDependencies__sveltejs_adapter_static: string;
		INIT_CWD: string;
		CHROME_DESKTOP: string;
		npm_package_scripts_preview: string;
		npm_lifecycle_script: string;
		CURSOR_AGENT: string;
		npm_config_version_tag_prefix: string;
		npm_package_devDependencies__sveltejs_vite_plugin_svelte: string;
		YARN_WRAP_OUTPUT: string;
		GHOSTTY_RESOURCES_DIR: string;
		XDG_SESSION_CLASS: string;
		TERM: string;
		TERMINFO: string;
		LC_IDENTIFICATION: string;
		npm_package_name: string;
		ZSH: string;
		npm_package_type: string;
		USER: string;
		EVERYSPHERE_RIPGREP_PATH: string;
		DISPLAY: string;
		npm_lifecycle_event: string;
		VSCODE_PID: string;
		SHLVL: string;
		npm_config_version_git_sign: string;
		npm_config_version_git_message: string;
		PAGER: string;
		LC_TELEPHONE: string;
		QT_IM_MODULE: string;
		LC_MEASUREMENT: string;
		VSCODE_CWD: string;
		XDG_VTNR: string;
		XDG_SESSION_ID: string;
		npm_config_user_agent: string;
		NO_COLOR: string;
		npm_execpath: string;
		VSCODE_CRASH_REPORTER_PROCESS_TYPE: string;
		XDG_RUNTIME_DIR: string;
		npm_config_strict_ssl: string;
		DEBUGINFOD_URLS: string;
		npm_package_scripts_dev: string;
		ELECTRON_NO_ATTACH_CONSOLE: string;
		GTK3_MODULES: string;
		GDK_BACKEND: string;
		npm_package_dependencies_svelte: string;
		PATH: string;
		GDMSESSION: string;
		npm_package_devDependencies__sveltejs_kit: string;
		CI: string;
		ORIGINAL_XDG_CURRENT_DESKTOP: string;
		DBUS_SESSION_BUS_ADDRESS: string;
		VSCODE_NLS_CONFIG: string;
		MAIL: string;
		npm_config_registry: string;
		npm_package_scripts_sync: string;
		npm_config_ignore_optional: string;
		npm_node_execpath: string;
		VSCODE_HANDLES_UNCAUGHT_ERRORS: string;
		OLDPWD: string;
		TERM_PROGRAM: string;
		CURSOR_TRACE_ID: string;
		npm_config_init_version: string;
		NODE_ENV: string;
		[key: `PUBLIC_${string}`]: undefined;
		[key: `${string}`]: string | undefined;
	}
}

/**
 * Similar to [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), but only includes variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`), and can therefore safely be exposed to client-side code.
 * 
 * Note that public dynamic environment variables must all be sent from the server to the client, causing larger network requests — when possible, use `$env/static/public` instead.
 * 
 * ```ts
 * import { env } from '$env/dynamic/public';
 * console.log(env.PUBLIC_DEPLOYMENT_SPECIFIC_VARIABLE);
 * ```
 */
declare module '$env/dynamic/public' {
	export const env: {
		[key: `PUBLIC_${string}`]: string | undefined;
	}
}
