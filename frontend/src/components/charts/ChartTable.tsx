import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";

interface ChartTableProps {
  label: string;
  /** First column is the row label; the rest are numbers and are right-aligned. */
  headers: string[];
  rows: string[][];
}

export default function ChartTable({ label, headers, rows }: ChartTableProps) {
  return (
    <TableContainer sx={{ maxHeight: 260 }}>
      <Table size="small" stickyHeader aria-label={label}>
        <TableHead>
          <TableRow>
            {headers.map((header, column) => (
              <TableCell key={header} align={column === 0 ? "left" : "right"}>
                {header}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row[0]}>
              {row.map((cell, column) => (
                <TableCell key={headers[column]} align={column === 0 ? "left" : "right"} sx={column ? { fontVariantNumeric: "tabular-nums" } : undefined}>
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
