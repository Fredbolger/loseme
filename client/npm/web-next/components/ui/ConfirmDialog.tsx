'use client';

import * as AlertDialog from '@radix-ui/react-alert-dialog';

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-[200] bg-black/50" />
        <AlertDialog.Content className="fixed left-1/2 top-1/2 z-[201] w-[360px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-bg-secondary p-6 shadow-xl">
          <AlertDialog.Title className="text-[15px] font-semibold text-text-primary">
            {title}
          </AlertDialog.Title>
          <AlertDialog.Description className="mt-2 text-[13px] text-text-secondary">
            {description}
          </AlertDialog.Description>
          <div className="mt-5 flex justify-end gap-3">
            <AlertDialog.Cancel asChild>
              <button className="rounded-md bg-bg-tertiary px-4 py-2 text-[13px] font-medium text-text-secondary hover:bg-bg-hover">
                {cancelLabel}
              </button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <button
                onClick={onConfirm}
                className={
                  destructive
                    ? 'rounded-md bg-red-700 px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90'
                    : 'rounded-md bg-accent-primary px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90'
                }
              >
                {confirmLabel}
              </button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
