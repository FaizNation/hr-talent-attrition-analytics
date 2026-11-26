import type { GenericRecord } from '../types'
import { formatCell } from '../utils/format'

export function GenericTable({ records }: { records: GenericRecord[] }) {
  if (records.length === 0) return <p className="empty">Tidak ada baris data.</p>
  const columns = Object.keys(records[0])

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th scope="col" key={column}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>
                  {formatCell(record[column] ?? null, column.includes('%'))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
