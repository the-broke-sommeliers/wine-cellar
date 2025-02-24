import React from 'react'
import { createRoot } from 'react-dom/client'
import { BarcodeScanner } from 'react-barcode-scanner'
import 'react-barcode-scanner/polyfill'

const Scanner = () => {
  const handleCapture = (captured) => {
    if (captured.length > 0) {
      window.location.href = '/wine/scan/' + captured[0].rawValue
    }
  }

  return <BarcodeScanner onCapture={handleCapture} options={{ formats: ['ean_13', 'ean_8', 'upc_a', 'code_39', 'itf'] }} />
}

const initScanner = () => {
  const root = createRoot(document.getElementById('scanner'))
  root.render(<Scanner />)
}

document.addEventListener('DOMContentLoaded', initScanner, false)
