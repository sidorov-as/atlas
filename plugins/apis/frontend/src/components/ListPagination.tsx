import { Pagination } from '@gravity-ui/uikit'

export const PAGE_SIZE_OPTIONS = [15, 30, 50, 100]
export const DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0]

/** Pagination footer shared by the Endpoints, Operations and Linked Services lists: 15/30/50/100 per page plus a page input. Renders nothing for an empty list. `onUpdate` receives the page to show — already reset to 1 when the page size changed. */
export function ListPagination({
  page,
  pageSize,
  total,
  onUpdate,
}: {
  page: number
  pageSize: number
  total: number
  onUpdate: (page: number, pageSize: number) => void
}) {
  if (total <= 0) return null
  return (
    <div style={{ marginTop: 16 }}>
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        pageSizeOptions={PAGE_SIZE_OPTIONS}
        showInput
        onUpdate={(nextPage, nextPageSize) => onUpdate(nextPageSize === pageSize ? nextPage : 1, nextPageSize)}
      />
    </div>
  )
}
