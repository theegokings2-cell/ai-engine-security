"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { useToast } from "@/hooks/use-toast"
import { X } from "lucide-react"

export function Toaster() {
  const { toasts, dismiss } = useToast()

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "pointer-events-auto flex w-full max-w-md rounded-lg bg-white p-4 shadow-lg ring-1 ring-black ring-opacity-5",
            toast.variant === "destructive" && "bg-red-50 ring-red-500"
          )}
        >
          <div className="flex-1">
            {toast.title && (
              <p
                className={cn(
                  "text-sm font-medium text-gray-900",
                  toast.variant === "destructive" && "text-red-800"
                )}
              >
                {toast.title}
              </p>
            )}
            {toast.description && (
              <p
                className={cn(
                  "mt-1 text-sm text-gray-500",
                  toast.variant === "destructive" && "text-red-600"
                )}
              >
                {toast.description}
              </p>
            )}
          </div>
          <button
            onClick={() => dismiss(toast.id)}
            className="ml-4 inline-flex text-gray-400 hover:text-gray-500"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      ))}
    </div>
  )
}
