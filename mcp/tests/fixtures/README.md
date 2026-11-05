# Fixture provenance

`buildings.synthetic.json` is synthetic contract data based on the checked-in
Flask response schema. The B41 IDs exercise the duplicate reported in the ticket;
its conflicting values are test inputs, not verified live metadata.

Zero review counts are synthetic inputs, not claims about the current service.
No removed production test reviews or reviewer identities are stored here.

Run `bun run fixtures:refresh` from a network-enabled environment to capture
timestamped, current samples under the ignored `live/` directory. Review captures
are sanitized. Live samples must be reviewed before promoting them to committed
regression fixtures; do not replace deterministic synthetic contracts blindly.

The ticket's separate MCP snapshot was not present when this service was built.
