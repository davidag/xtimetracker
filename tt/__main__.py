try:
    from tt import cli
except ImportError:
    from . import cli

cli.cli()
