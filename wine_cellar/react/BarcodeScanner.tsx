import { BarcodeDetector } from 'barcode-detector/ponyfill'
import { useEffect, useRef } from 'react'

type BarcodeFormat = NonNullable<
  NonNullable<ConstructorParameters<typeof BarcodeDetector>[0]>['formats']
>[number]

interface DetectedBarcode {
  rawValue: string
}

interface BarcodeScannerProps {
  onCapture: (barcodes: DetectedBarcode[]) => void
  options?: { formats?: string[] }
}

const DEFAULT_FORMATS: BarcodeFormat[] = [
  'ean_13',
  'ean_8',
  'upc_a',
  'code_39',
  'itf',
]

export function BarcodeScanner({ onCapture, options }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  // Keep a ref to the latest onCapture so the interval never captures a stale closure,
  // without adding onCapture to the effect's dependency array (which would restart the camera)
  const onCaptureRef = useRef(onCapture)
  onCaptureRef.current = onCapture

  const formatsKey = options?.formats?.join(',') ?? ''

  useEffect(() => {
    const video = videoRef.current
    if (!video) {
      return
    }

    let stream: MediaStream | null = null
    let timerId: ReturnType<typeof setInterval> | null = null

    // Derive formats from the stable formatsKey string so no extra deps are needed
    const formats = (
      formatsKey ? formatsKey.split(',') : DEFAULT_FORMATS
    ) as BarcodeFormat[]
    const detector = new BarcodeDetector({ formats })

    async function start(el: HTMLVideoElement) {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment',
            width: { ideal: 640 },
            height: { ideal: 1280 },
          },
        })
        el.srcObject = stream
        await el.play()
        timerId = setInterval(async () => {
          if (el.readyState >= el.HAVE_ENOUGH_DATA) {
            const found = await detector.detect(el)
            if (found.length) {
              onCaptureRef.current(found as DetectedBarcode[])
            }
          }
        }, 1000)
      } catch (err) {
        console.error('BarcodeScanner camera error:', err)
      }
    }

    start(video)
    return () => {
      if (timerId !== null) {
        clearInterval(timerId)
      }
      stream?.getTracks().forEach((t) => {
        t.stop()
      })
    }
  }, [formatsKey])

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      muted
      style={{ width: '100%' }}
    />
  )
}
