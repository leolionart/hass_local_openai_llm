"""Config flow for Local OpenAI LLM integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LLM_HASS_API,
    CONF_MODEL,
    CONF_NAME,
    CONF_PROMPT,
)
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TemplateSelector,
)
from openai import AsyncOpenAI, OpenAIError

from .const import (
    CONF_BASE_URL,
    CONF_GENERATE_DATA,
    CONF_GENERATE_IMAGE,
    CONF_MANUAL_PROMPTING,
    CONF_PARALLEL_TOOL_CALLS,
    CONF_SERVER_NAME,
    CONF_STRIP_EMOJIS,
    CONF_STRIP_EMPHASIS,
    CONF_STRIP_LATEX,
    CONF_SUPPORT_ATTACHMENTS,
    CONF_TEMPERATURE,
    DOMAIN,
    LOGGER,
    RECOMMENDED_CONVERSATION_OPTIONS,
)


class LocalAiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Local OpenAI LLM."""

    VERSION = 1

    @staticmethod
    def _sanitize_connection_input(user_input: dict[str, Any]) -> dict[str, Any]:
        """Normalize connection settings before storing them."""
        sanitized_input = user_input.copy()

        server_name = sanitized_input.get(CONF_SERVER_NAME)
        if isinstance(server_name, str):
            sanitized_input[CONF_SERVER_NAME] = server_name.strip() or "Local LLM Server"

        base_url = sanitized_input.get(CONF_BASE_URL)
        if isinstance(base_url, str):
            sanitized_input[CONF_BASE_URL] = base_url.strip()

        api_key = sanitized_input.get(CONF_API_KEY)
        if isinstance(api_key, str):
            api_key = api_key.strip()
            if api_key:
                sanitized_input[CONF_API_KEY] = api_key
            else:
                sanitized_input.pop(CONF_API_KEY, None)

        return sanitized_input

    @staticmethod
    def _get_connection_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
        """Return the schema used to configure the upstream OpenAI-compatible server."""
        defaults = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_SERVER_NAME,
                    default=defaults.get(CONF_SERVER_NAME, "Local LLM Server"),
                ): str,
                vol.Required(
                    CONF_BASE_URL,
                    default=defaults.get(CONF_BASE_URL, ""),
                ): str,
                vol.Optional(
                    CONF_API_KEY,
                    default=defaults.get(CONF_API_KEY, ""),
                ): str,
            }
        )

    async def _async_validate_connection(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate connection settings against the configured upstream server."""
        LOGGER.debug("Initialising OpenAI client with base_url: %s", user_input[CONF_BASE_URL])

        try:
            client = AsyncOpenAI(
                base_url=user_input.get(CONF_BASE_URL),
                api_key=user_input.get(CONF_API_KEY, ""),
                http_client=get_async_client(self.hass),
            )

            LOGGER.debug("Retrieving model list to ensure server is accessible")
            await client.models.list()
        except OpenAIError as err:
            LOGGER.exception("OpenAI Error: %s", err)
            return {"base": "cannot_connect"}
        except Exception as err:
            LOGGER.exception("Unexpected exception: %s", err)
            return {"base": "unknown"}

        LOGGER.debug("Server connection verified")
        return {}

    def _base_url_in_use(self, base_url: str, current_entry_id: str | None = None) -> bool:
        """Return True if another config entry already uses the same base URL."""
        return any(
            entry.entry_id != current_entry_id and entry.data.get(CONF_BASE_URL) == base_url
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this handler."""
        return {
            "conversation": ConversationFlowHandler,
            "ai_task_data": AITaskDataFlowHandler,
        }

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        LOGGER.debug("Config flow: step_user, input: %s", user_input)
        errors = {}
        if user_input is not None:
            user_input = self._sanitize_connection_input(user_input)
            if self._base_url_in_use(user_input[CONF_BASE_URL]):
                return self.async_abort(reason="already_configured")
            errors = await self._async_validate_connection(user_input)
            if not errors:
                return self.async_create_entry(
                    title=f"{user_input.get(CONF_SERVER_NAME, 'Local LLM Server')}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_connection_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle updating an existing connection."""
        entry = self._get_reconfigure_entry()
        errors = {}

        if user_input is not None:
            user_input = self._sanitize_connection_input(user_input)
            if self._base_url_in_use(user_input[CONF_BASE_URL], entry.entry_id):
                return self.async_abort(reason="already_configured")
            errors = await self._async_validate_connection(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._get_connection_schema(user_input or entry.data),
            errors=errors,
        )


class LocalAiSubentryFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for Local OpenAI LLM."""

    @staticmethod
    def strip_model_pathing(model_name: str) -> str:
        matches = re.search(r"([^/]*)\.gguf$", model_name.strip())
        return matches[1] if matches else model_name


class ConversationFlowHandler(LocalAiSubentryFlowHandler):
    """Handle subentry flow."""

    def get_llm_apis(self) -> list[SelectOptionDict]:
        return [
            SelectOptionDict(
                label=api.name,
                value=api.id,
            )
            for api in llm.async_get_apis(self.hass)
        ]

    async def get_schema(self, options=None):
        if options is None:
            options = {}
        llm_apis = self.get_llm_apis()
        client = self._get_entry().runtime_data

        try:
            response = await client.models.list()
            downloaded_models: list[SelectOptionDict] = [
                SelectOptionDict(
                    label=model.id,
                    value=model.id,
                )
                for model in response.data
            ]
            LOGGER.debug("Found models: %s", downloaded_models)
        except OpenAIError as err:
            LOGGER.exception(f"OpenAI Error retrieving models list: {err}")
            downloaded_models = []
        except Exception as err:
            LOGGER.exception(f"Unexpected exception retrieving models list: {err}")
            downloaded_models = []

        default_model_value = options.get(CONF_MODEL)
        if not default_model_value and downloaded_models:
            default_model_value = downloaded_models[0]["value"]
        default_model = default_model_value or "Local"
        default_title = self.strip_model_pathing(default_model)
        default_name = options.get(CONF_NAME) or f"{default_title} AI Agent"

        return vol.Schema(
            {
                vol.Optional(
                    CONF_NAME,
                    default=default_name,
                ): str,
                vol.Required(
                    CONF_MODEL,
                    default=default_model,
                ): SelectSelector(
                    SelectSelectorConfig(options=downloaded_models, custom_value=True)
                ),
                vol.Optional(
                    CONF_PROMPT,
                    default=options.get(CONF_PROMPT, RECOMMENDED_CONVERSATION_OPTIONS[CONF_PROMPT]),
                ): TemplateSelector(),
                vol.Optional(
                    CONF_LLM_HASS_API,
                    default=options.get(
                        CONF_LLM_HASS_API,
                        RECOMMENDED_CONVERSATION_OPTIONS[CONF_LLM_HASS_API],
                    ),
                ): SelectSelector(SelectSelectorConfig(options=llm_apis, multiple=True)),
                vol.Optional(
                    CONF_PARALLEL_TOOL_CALLS,
                    default=options.get(CONF_PARALLEL_TOOL_CALLS, True),
                ): bool,
                vol.Optional(
                    CONF_STRIP_EMOJIS,
                    default=options.get(CONF_STRIP_EMOJIS, True),
                ): bool,
                vol.Optional(
                    CONF_STRIP_EMPHASIS,
                    default=options.get(CONF_STRIP_EMPHASIS, True),
                ): bool,
                vol.Optional(
                    CONF_STRIP_LATEX,
                    default=options.get(CONF_STRIP_LATEX, True),
                ): bool,
                vol.Optional(
                    CONF_MANUAL_PROMPTING,
                    default=options.get(CONF_MANUAL_PROMPTING, False),
                ): bool,
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=options.get(CONF_TEMPERATURE, 1),
                ): NumberSelector(
                    NumberSelectorConfig(min=0, max=1, step=0.05, mode=NumberSelectorMode.SLIDER)
                ),
            }
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """User flow to create a sensor subentry."""
        if user_input is not None:
            user_input = user_input.copy()
            raw_name = user_input.get(CONF_NAME)
            custom_name = raw_name.strip() if isinstance(raw_name, str) else None
            if custom_name:
                user_input[CONF_NAME] = custom_name
            else:
                user_input.pop(CONF_NAME, None)

            model_name = self.strip_model_pathing(user_input.get(CONF_MODEL, "Local"))
            entry_title = custom_name or f"{model_name} AI Agent"

            return self.async_create_entry(title=entry_title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=await self.get_schema(),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to create a sensor subentry."""
        if user_input is not None:
            user_input = user_input.copy()
            raw_name = user_input.get(CONF_NAME)
            custom_name = raw_name.strip() if isinstance(raw_name, str) else None
            if custom_name:
                user_input[CONF_NAME] = custom_name
            else:
                user_input.pop(CONF_NAME, None)

            model_name = self.strip_model_pathing(user_input.get(CONF_MODEL, "Local"))
            entry_title = custom_name or f"{model_name} AI Agent"

            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                title=entry_title,
                data=user_input,
            )

        options = self._get_reconfigure_subentry().data.copy()

        # Filter out any tool providers that no longer exist
        hass_apis = [api.get("value") for api in self.get_llm_apis()]
        options["llm_hass_api"] = [
            api for api in options.get("llm_hass_api", []) if api in hass_apis
        ]

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=await self.get_schema(options),
        )


class AITaskDataFlowHandler(LocalAiSubentryFlowHandler):
    """Handle subentry flow."""

    async def get_schema(self, options=None):
        if options is None:
            options = {}
        try:
            client = self._get_entry().runtime_data
            response = await client.models.list()
            downloaded_models: list[SelectOptionDict] = [
                SelectOptionDict(
                    label=model.id,
                    value=model.id,
                )
                for model in response.data
            ]
        except OpenAIError as err:
            LOGGER.exception(f"OpenAI Error retrieving models list: {err}")
            downloaded_models = []
        except Exception as err:
            LOGGER.exception(f"Unexpected exception retrieving models list: {err}")
            downloaded_models = []

        default_model_value = options.get(CONF_MODEL)
        if not default_model_value and downloaded_models:
            default_model_value = downloaded_models[0]["value"]
        default_model = default_model_value or "Local"

        default_title = self.strip_model_pathing(default_model)
        default_name = options.get(CONF_NAME) or f"{default_title} AI Task"

        return vol.Schema(
            {
                vol.Optional(
                    CONF_NAME,
                    default=default_name,
                ): str,
                vol.Required(
                    CONF_MODEL,
                    default=default_model,
                ): SelectSelector(
                    SelectSelectorConfig(options=downloaded_models, custom_value=True)
                ),
                vol.Optional(
                    CONF_GENERATE_DATA,
                    default=options.get(CONF_GENERATE_DATA, True),
                ): bool,
                vol.Optional(
                    CONF_GENERATE_IMAGE,
                    default=options.get(CONF_GENERATE_IMAGE, True),
                ): bool,
                vol.Optional(
                    CONF_SUPPORT_ATTACHMENTS,
                    default=options.get(CONF_SUPPORT_ATTACHMENTS, True),
                ): bool,
                vol.Optional(
                    CONF_STRIP_EMOJIS,
                    default=options.get(CONF_STRIP_EMOJIS, True),
                ): bool,
                vol.Optional(
                    CONF_STRIP_EMPHASIS,
                    default=options.get(CONF_STRIP_EMPHASIS, True),
                ): bool,
                vol.Optional(
                    CONF_STRIP_LATEX,
                    default=options.get(CONF_STRIP_LATEX, True),
                ): bool,
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=options.get(CONF_TEMPERATURE, 1),
                ): NumberSelector(
                    NumberSelectorConfig(min=0, max=1, step=0.05, mode=NumberSelectorMode.SLIDER)
                ),
            }
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """User flow to create a sensor subentry."""
        if user_input is not None:
            user_input = user_input.copy()
            raw_name = user_input.get(CONF_NAME)
            custom_name = raw_name.strip() if isinstance(raw_name, str) else None
            if custom_name:
                user_input[CONF_NAME] = custom_name
            else:
                user_input.pop(CONF_NAME, None)

            model_name = self.strip_model_pathing(user_input.get(CONF_MODEL, "Local"))
            entry_title = custom_name or f"{model_name} AI Task"

            return self.async_create_entry(title=entry_title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=await self.get_schema(),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to reconfigure a sensor subentry."""
        if user_input is not None:
            user_input = user_input.copy()
            raw_name = user_input.get(CONF_NAME)
            custom_name = raw_name.strip() if isinstance(raw_name, str) else None
            if custom_name:
                user_input[CONF_NAME] = custom_name
            else:
                user_input.pop(CONF_NAME, None)

            model_name = self.strip_model_pathing(user_input.get(CONF_MODEL, "Local"))
            entry_title = custom_name or f"{model_name} AI Task"

            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                title=entry_title,
                data=user_input,
            )

        options = self._get_reconfigure_subentry().data.copy()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=await self.get_schema(options),
        )
