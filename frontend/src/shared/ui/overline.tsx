import type { ComponentProps } from 'react'

import { classNames } from '@/shared/lib/class-names'

import s from './overline.module.css'

export function Overline({ className, ...props }: ComponentProps<'span'>) {
  return <span className={classNames(s.root, className)} {...props} />
}
