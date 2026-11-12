import * as DialogPrimitive from '@radix-ui/react-dialog'
import * as SwitchPrimitive from '@radix-ui/react-switch'
import { X } from 'lucide-react'
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(' ')
}

type Variant = 'primary' | 'ghost' | 'danger' | 'subtle'

export function Button({
  variant = 'subtle',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const styles: Record<Variant, string> = {
    primary: 'bg-sol text-ink-950 hover:bg-sky-300 font-semibold',
    ghost: 'bg-transparent hover:bg-ink-700 text-ink-100',
    danger: 'bg-bad/15 text-bad hover:bg-bad/25 border border-bad/40',
    subtle: 'bg-ink-700 hover:bg-ink-600 text-ink-100 border border-ink-600',
  }
  return (
    <button
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm transition-colors',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sol disabled:opacity-40',
        'disabled:cursor-not-allowed',
        styles[variant],
        className,
      )}
      {...props}
    />
  )
}

export function Panel({
  title,
  icon,
  actions,
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLElement> & { title?: ReactNode; icon?: ReactNode; actions?: ReactNode }) {
  return (
    <section
      className={cx('flex min-h-0 flex-col rounded-2xl border border-ink-700 bg-ink-850/80 backdrop-blur', className)}
      {...rest}
    >
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-ink-700 px-4 py-2.5">
          <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-ink-300">
            {icon}
            {title}
          </h2>
          {actions}
        </header>
      )}
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </section>
  )
}

export function Badge({ tone = 'neutral', children, className }: { tone?: string; children: ReactNode; className?: string }) {
  const tones: Record<string, string> = {
    neutral: 'bg-ink-700 text-ink-300 border-ink-600',
    sol: 'bg-sol/15 text-sol border-sol/40',
    opus: 'bg-opus/15 text-opus border-opus/40',
    ok: 'bg-ok/15 text-ok border-ok/40',
    bad: 'bg-bad/15 text-bad border-bad/40',
    warn: 'bg-warn/15 text-warn border-warn/40',
    star: 'bg-star/15 text-star border-star/40',
  }
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        tones[tone] ?? tones.neutral,
        className,
      )}
    >
      {children}
    </span>
  )
}

export function Switch({
  checked,
  onCheckedChange,
  id,
  label,
}: {
  checked: boolean
  onCheckedChange: (v: boolean) => void
  id: string
  label: string
}) {
  return (
    <SwitchPrimitive.Root
      id={id}
      aria-label={label}
      checked={checked}
      onCheckedChange={onCheckedChange}
      className="relative h-6 w-11 shrink-0 rounded-full bg-ink-600 transition-colors data-[state=checked]:bg-ok focus-visible:outline-2 focus-visible:outline-sol"
    >
      <SwitchPrimitive.Thumb className="block h-5 w-5 translate-x-0.5 rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-[22px]" />
    </SwitchPrimitive.Root>
  )
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[min(640px,94vw)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-ink-600 bg-ink-850 p-6 shadow-2xl scroll-thin">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <DialogPrimitive.Title className="text-lg font-semibold">{title}</DialogPrimitive.Title>
              {description && (
                <DialogPrimitive.Description className="mt-1 text-sm text-ink-300">{description}</DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close className="rounded-md p-1 text-ink-300 hover:bg-ink-700" aria-label="Close">
              <X size={18} />
            </DialogPrimitive.Close>
          </div>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-400">{label}</div>
      <div className={cx('mt-0.5 truncate text-xl font-semibold tabular-nums', tone)}>{value}</div>
      {sub && <div className="truncate text-xs text-ink-400">{sub}</div>}
    </div>
  )
}
