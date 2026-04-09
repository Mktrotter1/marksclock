"""CLI entry point for marksclock."""

from __future__ import annotations

import json

import click
import uvicorn

from marksclock.config import settings


def _out(data: dict | list) -> None:
    """Pretty-print API response."""
    click.echo(json.dumps(data, indent=2))


def _client(server: str) -> "MarksclockClient":
    from marksclock.client import MarksclockClient
    return MarksclockClient(server)


@click.group()
def main() -> None:
    """marksclock — exhaustive time utility suite."""


@main.command()
@click.option("--host", default=None, help=f"Bind host (default: {settings.host})")
@click.option("--port", default=None, type=int, help=f"Bind port (default: {settings.port})")
def serve(host: str | None, port: int | None) -> None:
    """Start the marksclock web server."""
    uvicorn.run(
        "marksclock.app:create_app",
        host=host or settings.host,
        port=port or settings.port,
        factory=True,
    )


@main.command()
def info() -> None:
    """Show current configuration."""
    click.echo(f"Host:     {settings.host}")
    click.echo(f"Port:     {settings.port}")
    click.echo(f"Timezone: {settings.default_timezone}")
    click.echo(f"State:    {settings.state_dir}")
    if settings.home_lat and settings.home_lon:
        click.echo(f"Location: {settings.home_lat}, {settings.home_lon}")


# ── Remote client commands ──────────────────────────────────────────
# Usage: marksclock client --server http://192.168.1.100:8080 timer list

@main.group()
@click.option("--server", "-s", default="http://localhost:8080",
              envvar="MARKSCLOCK_SERVER", show_envvar=True,
              help="marksclock server URL")
@click.pass_context
def client(ctx: click.Context, server: str) -> None:
    """Remote client — talk to a running marksclock server."""
    ctx.ensure_object(dict)
    ctx.obj["client"] = _client(server)


# -- clock --

@client.command("clock")
@click.option("--tz", default=None, help="Timezone")
@click.pass_context
def client_clock(ctx: click.Context, tz: str | None) -> None:
    """Get current time from server."""
    _out(ctx.obj["client"].clock(tz))


# -- timer --

@client.group("timer")
@click.pass_context
def client_timer(ctx: click.Context) -> None:
    """Manage timers on the server."""


@client_timer.command("list")
@click.pass_context
def timer_list(ctx: click.Context) -> None:
    """List all timers."""
    _out(ctx.obj["client"].timer_list())


@client_timer.command("create")
@click.argument("label")
@click.argument("seconds", type=float)
@click.pass_context
def timer_create(ctx: click.Context, label: str, seconds: float) -> None:
    """Create a timer. LABEL is the name, SECONDS is the countdown duration."""
    result = ctx.obj["client"].timer_create(label, seconds)
    # Auto-start
    ctx.obj["client"].timer_start(result["id"])
    click.echo(f"Timer '{label}' created and started (id: {result['id']})")


@client_timer.command("start")
@click.argument("timer_id")
@click.pass_context
def timer_start(ctx: click.Context, timer_id: str) -> None:
    """Start a paused timer."""
    _out(ctx.obj["client"].timer_start(timer_id))


@client_timer.command("pause")
@click.argument("timer_id")
@click.pass_context
def timer_pause(ctx: click.Context, timer_id: str) -> None:
    """Pause a running timer."""
    _out(ctx.obj["client"].timer_pause(timer_id))


@client_timer.command("reset")
@click.argument("timer_id")
@click.pass_context
def timer_reset(ctx: click.Context, timer_id: str) -> None:
    """Reset a timer."""
    _out(ctx.obj["client"].timer_reset(timer_id))


@client_timer.command("delete")
@click.argument("timer_id")
@click.pass_context
def timer_delete(ctx: click.Context, timer_id: str) -> None:
    """Delete a timer."""
    _out(ctx.obj["client"].timer_delete(timer_id))


# -- stopwatch --

@client.group("stopwatch")
@click.pass_context
def client_stopwatch(ctx: click.Context) -> None:
    """Manage stopwatch on the server."""


@client_stopwatch.command("status")
@click.pass_context
def sw_status(ctx: click.Context) -> None:
    """Get stopwatch state."""
    _out(ctx.obj["client"].stopwatch())


@client_stopwatch.command("start")
@click.pass_context
def sw_start(ctx: click.Context) -> None:
    """Start stopwatch."""
    _out(ctx.obj["client"].stopwatch_start())


@client_stopwatch.command("stop")
@click.pass_context
def sw_stop(ctx: click.Context) -> None:
    """Stop stopwatch."""
    _out(ctx.obj["client"].stopwatch_stop())


@client_stopwatch.command("lap")
@click.pass_context
def sw_lap(ctx: click.Context) -> None:
    """Record a lap."""
    _out(ctx.obj["client"].stopwatch_lap())


@client_stopwatch.command("reset")
@click.pass_context
def sw_reset(ctx: click.Context) -> None:
    """Reset stopwatch."""
    _out(ctx.obj["client"].stopwatch_reset())


# -- alarm --

@client.group("alarm")
@click.pass_context
def client_alarm(ctx: click.Context) -> None:
    """Manage alarms on the server."""


@client_alarm.command("list")
@click.pass_context
def alarm_list(ctx: click.Context) -> None:
    """List all alarms."""
    _out(ctx.obj["client"].alarm_list())


@client_alarm.command("create")
@click.argument("label")
@click.argument("time_str")
@click.pass_context
def alarm_create(ctx: click.Context, label: str, time_str: str) -> None:
    """Create an alarm. TIME_STR is HH:MM format."""
    result = ctx.obj["client"].alarm_create(label, time_str)
    click.echo(f"Alarm '{label}' at {time_str} created (id: {result['id']})")


@client_alarm.command("toggle")
@click.argument("alarm_id")
@click.pass_context
def alarm_toggle(ctx: click.Context, alarm_id: str) -> None:
    """Toggle alarm on/off."""
    _out(ctx.obj["client"].alarm_toggle(alarm_id))


@client_alarm.command("delete")
@click.argument("alarm_id")
@click.pass_context
def alarm_delete(ctx: click.Context, alarm_id: str) -> None:
    """Delete an alarm."""
    _out(ctx.obj["client"].alarm_delete(alarm_id))


# -- pomodoro --

@client.group("pomodoro")
@click.pass_context
def client_pomodoro(ctx: click.Context) -> None:
    """Manage pomodoro on the server."""


@client_pomodoro.command("status")
@click.pass_context
def pom_status(ctx: click.Context) -> None:
    """Get pomodoro state."""
    _out(ctx.obj["client"].pomodoro())


@client_pomodoro.command("start")
@click.pass_context
def pom_start(ctx: click.Context) -> None:
    """Start pomodoro."""
    _out(ctx.obj["client"].pomodoro_start())


@client_pomodoro.command("pause")
@click.pass_context
def pom_pause(ctx: click.Context) -> None:
    """Pause pomodoro."""
    _out(ctx.obj["client"].pomodoro_pause())


@client_pomodoro.command("skip")
@click.pass_context
def pom_skip(ctx: click.Context) -> None:
    """Skip to next phase."""
    _out(ctx.obj["client"].pomodoro_skip())


@client_pomodoro.command("reset")
@click.pass_context
def pom_reset(ctx: click.Context) -> None:
    """Reset pomodoro."""
    _out(ctx.obj["client"].pomodoro_reset())


# -- worldclock --

@client.group("worldclock")
@click.pass_context
def client_worldclock(ctx: click.Context) -> None:
    """Manage world clock zones on the server."""


@client_worldclock.command("list")
@click.pass_context
def wc_list(ctx: click.Context) -> None:
    """List world clock zones."""
    _out(ctx.obj["client"].worldclock())


@client_worldclock.command("add")
@click.argument("timezone")
@click.pass_context
def wc_add(ctx: click.Context, timezone: str) -> None:
    """Add a timezone."""
    _out(ctx.obj["client"].worldclock_add(timezone))


@client_worldclock.command("remove")
@click.argument("timezone")
@click.pass_context
def wc_remove(ctx: click.Context, timezone: str) -> None:
    """Remove a timezone."""
    _out(ctx.obj["client"].worldclock_remove(timezone))


if __name__ == "__main__":
    main()
