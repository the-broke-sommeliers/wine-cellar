import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BarcodeScanner, DetectedBarcode } from 'react-barcode-scanner'
// @ts-ignore
import django from 'django'

import { BarcodeDetector, prepareZXingModule } from 'barcode-detector/ponyfill'

const translated = {
  advanced: django.gettext('Advanced'),
  helptext: django.gettext(
    "Choose the type of barcode you want to scan, sometimes this can help if scanning doesn't work."
  ),
}

const Scanner = () => {
  const [selectedFormat, setSelectedFormat] = useState('any')
  const defaultFormats = ['ean_13', 'ean_8', 'upc_a', 'code_39', 'itf']

  const handleCapture = (barcodes:  DetectedBarcode[]) => {
    if (barcodes.length > 0) {
      window.location.href = '/wine/scan/' + barcodes[0].rawValue
    }
  }

  return (
    <>
      <section className="form__scanner__details">
        <details>
          <summary>{translated.advanced}</summary>
          <p className="form-hint">{translated.helptext}</p>
          <select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
          >
            <option value="">{django.gettext('All')}</option>
            <option value="code_39">Code 39</option>
            <option value="code_93">Code 93</option>
            <option value="code_128">Code 128</option>
            <option value="ean_8">EAN-8</option>
            <option value="ean_13">EAN-13</option>
            <option value="itf">ITF</option>
            <option value="upc_a">UPC-A</option>
            <option value="upc_e">UPC-E</option>
          </select>
        </details>
      </section>
      <section className="form__scanner">
        <BarcodeScanner
          onCapture={handleCapture}
          options={{
            formats: selectedFormat ? [selectedFormat] : defaultFormats,
          }}
        />
        <div className="overlay">
          <div className="overlay-element top-left" />
          <div className="overlay-element top-right" />
          <div className="overlay-element bottom-left" />
          <div className="overlay-element bottom-right" />
        </div>
      </section>
    </>
  )
}

const initScanner = () => {
  const container = document.getElementById('scanner')
  if (container) {
    const root = createRoot(container)
    // Override the locateFile function
    prepareZXingModule({
      overrides: {
        // @ts-ignore
        locateFile: (path, prefix) => {
          if (path.endsWith('.wasm')) {
            return container.dataset.zxing_wasm_url
          }
          return prefix + path
        },
      },
    })
    // @ts-ignore
    globalThis.BarcodeDetector ??= BarcodeDetector
    root.render(<Scanner />)
  }
}

document.addEventListener('DOMContentLoaded', initScanner, false)
