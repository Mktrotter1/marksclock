"""CLI entry point for markslamp."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text

from markslamp.models import SwitchType
from markslamp.protocols import ALL_PROTOCOLS
from markslamp.scanner import Scanner
from markslamp.switch_manager import SwitchManager

console = Console()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )


def build_lamp_table(mgr: SwitchManager) -> Table:
    """Build a rich table showing all lamps and their switches."""
    table = Table(title="Discovered Lamps & Switches", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Lamp", style="bold cyan")
    table.add_column("Protocol", style="magenta")
    table.add_column("IP", style="green")
    table.add_column("Switch", style="yellow")
    table.add_column("Type", style="dim")
    table.add_column("Value", style="bold white")

    idx = 1
    for lamp_id, lamp in mgr.lamps.items():
        first = True
        for sw_name, sw in lamp.switches.items():
            table.add_row(
                str(idx) if first else "",
                lamp.display_name if first else "",
                lamp.protocol if first else "",
                lamp.ip if first else "",
                sw_name,
                sw.switch_type.value,
                sw.display,
            )
            first = False
        if lamp.switches:
            idx += 1

    return table


async def run_scan(timeout: float, protocols: list[str] | None) -> SwitchManager:
    """Run the scan and connect flow."""
    all_protos = [p() for p in ALL_PROTOCOLS]

    if protocols:
        proto_names = {p.lower() for p in protocols}
        all_protos = [p for p in all_protos if p.name in proto_names]

    console.print(f"\n[bold]Scanning with {len(all_protos)} protocols (timeout={timeout}s)...[/bold]\n")

    scanner = Scanner(all_protos, timeout=timeout)

    with console.status("[bold green]Scanning network for lamps..."):
        lamps = await scanner.scan()

    if not lamps:
        console.print("[yellow]No lamps found on the network.[/yellow]")
        console.print("Tips:")
        console.print("  - Ensure lamps are powered on and connected to the same network")
        console.print("  - Try increasing timeout: markslamp scan --timeout 15")
        console.print("  - Check firewall rules for mDNS (5353/udp) and SSDP (1900/udp)")
        return SwitchManager(all_protos)

    console.print(f"[green]Found {len(lamps)} lamp(s). Connecting...[/green]\n")

    with console.status("[bold green]Connecting and reading switch states..."):
        connected = await scanner.connect_all()

    mgr = SwitchManager(all_protos)
    mgr.register_all(connected)

    return mgr


async def interactive_loop(mgr: SwitchManager) -> None:
    """Interactive control loop."""
    lamp_list = list(mgr.lamps.values())

    while True:
        console.print()
        console.print(build_lamp_table(mgr))
        console.print()
        console.print("[dim]Commands: (lamp#).(switch) = value | toggle (lamp#) | refresh (lamp#) | rescan | quit[/dim]")

        try:
            cmd = Prompt.ask("\n[bold]markslamp>")
        except (EOFError, KeyboardInterrupt):
            break

        cmd = cmd.strip()
        if not cmd or cmd in ("q", "quit", "exit"):
            break

        if cmd == "rescan":
            console.print("[yellow]Rescanning...[/yellow]")
            return  # Signal to rescan

        parts = cmd.split()
        if parts[0] == "toggle" and len(parts) == 2:
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(lamp_list):
                    ok = await mgr.toggle_power(lamp_list[idx].id)
                    console.print(f"[{'green' if ok else 'red'}]{'OK' if ok else 'FAILED'}[/]")
                else:
                    console.print("[red]Invalid lamp number[/red]")
            except ValueError:
                console.print("[red]Usage: toggle <lamp#>[/red]")
            continue

        if parts[0] == "refresh" and len(parts) == 2:
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(lamp_list):
                    state = await mgr.refresh_state(lamp_list[idx].id)
                    console.print(f"State: {state}")
                else:
                    console.print("[red]Invalid lamp number[/red]")
            except ValueError:
                console.print("[red]Usage: refresh <lamp#>[/red]")
            continue

        # Parse: 1.brightness = 128
        if "=" in cmd:
            lhs, rhs = cmd.split("=", 1)
            lhs = lhs.strip()
            rhs = rhs.strip()

            if "." in lhs:
                lamp_num, switch_name = lhs.split(".", 1)
                try:
                    idx = int(lamp_num) - 1
                    if 0 <= idx < len(lamp_list):
                        lamp = lamp_list[idx]
                        sw = lamp.switches.get(switch_name.strip())
                        if sw:
                            value = _parse_value(sw, rhs)
                            ok = await mgr.set_switch(lamp.id, switch_name.strip(), value)
                            console.print(f"[{'green' if ok else 'red'}]{'OK' if ok else 'FAILED'}[/]")
                        else:
                            console.print(f"[red]Switch '{switch_name}' not found[/red]")
                    else:
                        console.print("[red]Invalid lamp number[/red]")
                except (ValueError, IndexError) as e:
                    console.print(f"[red]Error: {e}[/red]")
            continue

        console.print("[yellow]Unknown command. Use: (lamp#).(switch) = value | toggle (lamp#) | quit[/yellow]")


def _parse_value(sw: "Switch", raw: str) -> object:
    """Parse a raw string value into the appropriate type for a switch."""
    if sw.switch_type == SwitchType.TOGGLE:
        return raw.lower() in ("1", "true", "on", "yes")
    if sw.switch_type == SwitchType.RANGE:
        return float(raw) if "." in raw else int(raw)
    if sw.switch_type == SwitchType.COLOR:
        parts = raw.strip("[]()").split(",")
        return [int(p.strip()) for p in parts]
    return raw


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """markslamp - Scan, discover, and control smart lamps."""
    setup_logging(verbose)


@cli.command()
@click.option("-t", "--timeout", default=5.0, help="Discovery timeout in seconds")
@click.option("-p", "--protocol", multiple=True, help="Only scan specific protocols")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def scan(timeout: float, protocol: tuple[str, ...], json_output: bool) -> None:
    """Scan for lamps on the network."""
    import json as json_mod

    mgr = asyncio.run(run_scan(timeout, list(protocol) if protocol else None))

    if json_output:
        console.print_json(json_mod.dumps(mgr.summary(), default=str))
    else:
        console.print(build_lamp_table(mgr))
        summary = mgr.summary()
        console.print(
            f"\n[bold]{summary['connected_lamps']} lamp(s), "
            f"{summary['total_switches']} switch(es)[/bold]"
        )


@cli.command()
@click.option("-t", "--timeout", default=5.0, help="Discovery timeout in seconds")
@click.option("-p", "--protocol", multiple=True, help="Only scan specific protocols")
def control(timeout: float, protocol: tuple[str, ...]) -> None:
    """Interactive lamp control."""
    async def _run() -> None:
        while True:
            mgr = await run_scan(timeout, list(protocol) if protocol else None)
            if not mgr.lamps:
                return
            result = await interactive_loop(mgr)
            if result is None:
                break  # quit

    asyncio.run(_run())


@cli.command()
@click.option("-t", "--timeout", default=5.0, help="Discovery timeout in seconds")
@click.option("-p", "--protocol", multiple=True, help="Only scan specific protocols")
@click.option("-o", "--output", default="markslamp_state.json", help="Output file")
def snapshot(timeout: float, protocol: tuple[str, ...], output: str) -> None:
    """Save current lamp states to a JSON file."""
    from pathlib import Path

    async def _run() -> None:
        mgr = await run_scan(timeout, list(protocol) if protocol else None)
        if mgr.lamps:
            mgr.save_state(Path(output))
            console.print(f"[green]State saved to {output}[/green]")

    asyncio.run(_run())


@cli.command()
@click.option("-t", "--timeout", default=5.0, help="Discovery timeout in seconds")
@click.option("-p", "--protocol", multiple=True, help="Only scan specific protocols")
@click.option("--host", default="0.0.0.0", help="Bind address (0.0.0.0 for LAN access)")
@click.option("--port", default=8420, help="Web UI port")
def serve(timeout: float, protocol: tuple[str, ...], host: str, port: int) -> None:
    """Start web UI server (access from phone/tablet on LAN)."""
    import socket
    import uvicorn
    from markslamp.web import create_app

    create_app(timeout=timeout, protocols=list(protocol) if protocol else None)

    # Show LAN IP for easy phone access
    lan_ip = _get_lan_ip()
    console.print(f"\n[bold green]markslamp web UI starting[/bold green]")
    console.print(f"  Local:   http://localhost:{port}")
    if lan_ip:
        console.print(f"  Network: http://{lan_ip}:{port}")
    console.print(f"\n  Open on your Z Fold 6 or any device on the same network!\n")

    uvicorn.run("markslamp.web:app", host=host, port=port, log_level="info")


def _get_lan_ip() -> str:
    """Get the machine's LAN IP address."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


@cli.command(name="list-protocols")
def list_protocols() -> None:
    """List all supported protocols."""
    table = Table(title="Supported Protocols")
    table.add_column("Protocol", style="bold cyan")
    table.add_column("Discovery", style="green")
    table.add_column("Library", style="yellow")

    protocols_info = [
        ("wled", "mDNS (_wled._tcp)", "aiohttp (REST)"),
        ("tuya", "UDP broadcast (6666/6667)", "tinytuya"),
        ("lifx", "UDP broadcast (56700)", "lifxlan"),
        ("yeelight", "SSDP multicast", "yeelight"),
        ("magic_home", "UDP broadcast (48899)", "flux_led"),
        ("tasmota", "mDNS (_http._tcp)", "aiohttp (REST)"),
        ("esphome", "mDNS (_esphomelib._tcp)", "aioesphomeapi"),
        ("hue", "mDNS (_hue._tcp)", "phue + aiohttp"),
        ("shelly", "mDNS (_http._tcp)", "aiohttp (REST)"),
        ("govee", "UDP multicast (4001)", "raw UDP"),
        ("elgato", "mDNS (_elg._tcp)", "aiohttp (REST)"),
    ]

    for name, discovery, lib in protocols_info:
        table.add_row(name, discovery, lib)

    console.print(table)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
