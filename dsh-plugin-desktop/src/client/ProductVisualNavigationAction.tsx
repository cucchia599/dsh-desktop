import type { PropsRuntime } from '@deepseek-ai/dsh-client-ui-slots'
import type {} from '@deepseek-ai/dsh-client-ui-sidebar/client'
import type { ReactElement } from 'react'

type Props = PropsRuntime<'sidebar.footer.action'>

export function ProductVisualNavigationAction({ wide }: Props): ReactElement {
  return (
    <button
      type="button"
      className="dshProductVisualNavAction"
      aria-label="商品视觉工作台"
      title="商品视觉工作台"
      onClick={() => { window.location.assign('/product-visual-workbench/') }}
    >
      <span aria-hidden>✦</span>
      {wide ? <span>商品视觉</span> : null}
    </button>
  )
}
