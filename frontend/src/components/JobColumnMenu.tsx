import { GridColumnMenu, type GridColumnMenuItemProps, type GridColumnMenuProps } from "@mui/x-data-grid";
import { isFilterField } from "../api/jobFilterFields";
import ColumnFilterForm from "./ColumnFilterForm";

function FilterMenuItem({ colDef }: GridColumnMenuItemProps) {
  return isFilterField(colDef.field) ? <ColumnFilterForm field={colDef.field} /> : null;
}

/**
 * The grid's column menu: sort ascending/descending, then this column's filter, then the column list.
 * The grid's own filter item is removed because the free grid allows only one active filter; ours
 * edits the page's filters directly, so filters on several columns combine.
 */
export default function JobColumnMenu(props: GridColumnMenuProps) {
  return (
    <GridColumnMenu
      {...props}
      slots={{ columnMenuFilterItem: null, columnMenuUserItem: FilterMenuItem }}
      slotProps={{ columnMenuUserItem: { displayOrder: 15 } }}
    />
  );
}
