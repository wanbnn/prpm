# Remote release verification

`prpm verify <package>` validates published artifacts against the repository metadata and inspects every wheel `RECORD` entry.

## Resource model

Remote verification is intentionally sequential and bounded by one artifact at a time.

Before the streaming verifier, every downloaded wheel and source distribution remained in the temporary directory until the complete release finished. Peak temporary disk usage therefore grew with the sum of all published artifacts. The SHA-256 check also reread every downloaded file from disk after the network transfer.

The verifier now computes SHA-256 and byte count while streaming the download, validates both digest and the size reported by the package index, inspects wheel contents when applicable, and deletes the artifact before downloading the next one.

For a release containing artifacts of sizes `s1..sn`:

- previous peak temporary storage: approximately `sum(s1..sn)`;
- current peak temporary storage: approximately `max(s1..sn)`;
- non-wheel SHA-256 file passes after download: reduced from one full reread to zero.

Network coverage is unchanged: PRPM still validates every artifact returned for the selected release. Wheel verification also remains unchanged and continues checking every hashed `RECORD` entry.

## Failure behavior

Temporary artifacts are removed even when hash or size validation fails. A repository response with a missing or divergent SHA-256 is rejected, as before. A repository-provided artifact size that does not match the actual streamed byte count is now rejected as an additional consistency check.
