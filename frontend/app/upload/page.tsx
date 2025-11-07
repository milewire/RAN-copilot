'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Upload as UploadIcon, File, Loader2 } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Debug: Log API URL (only in browser)
if (typeof window !== 'undefined') {
  console.log('API URL:', API_URL)
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const router = useRouter()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      const fileName = selectedFile.name.toLowerCase()
      if (fileName.endsWith('.xml.gz') || fileName.endsWith('.gz') || fileName.endsWith('.zip') || fileName.endsWith('.xml')) {
        setFile(selectedFile)
        setError(null)
      } else {
        setError('Please select a .xml.gz, .gz, .zip, or .xml file')
        setFile(null)
      }
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first')
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(false)

    try {
      const formData = new FormData()
      formData.append('file', file)

      // Upload file
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minute timeout for large files
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            console.log(`Upload progress: ${percentCompleted}%`)
          }
        },
      })

      setSuccess(true)
      setUploading(false)

      // Automatically analyze
      handleAnalyze()
    } catch (err: any) {
      console.error('Upload error:', err)
      let errorMessage = 'Upload failed'
      
      if (err.response) {
        // Server responded with error
        errorMessage = err.response.data?.detail || err.response.data?.message || `Server error: ${err.response.status}`
      } else if (err.request) {
        // Request made but no response
        errorMessage = `Cannot connect to server. Please check that ${API_URL} is accessible.`
      } else if (err.code === 'ECONNABORTED') {
        errorMessage = 'Upload timeout. The file may be too large or the connection is slow.'
      } else {
        errorMessage = err.message || 'Upload failed'
      }
      
      setError(errorMessage)
      setUploading(false)
    }
  }

  const handleAnalyze = async () => {
    if (!file) return

    setAnalyzing(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post(`${API_URL}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      // Store results in sessionStorage (only in browser)
      if (typeof window !== 'undefined') {
        try {
          sessionStorage.setItem('rcaResults', JSON.stringify(response.data))
          sessionStorage.setItem('kpiData', JSON.stringify(response.data.kpi_data))
        } catch (error) {
          console.error('Error storing data in sessionStorage:', error)
        }
      }

      // Navigate to dashboard
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis failed')
      setAnalyzing(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Upload PM Data</h1>
        <p className="text-muted-foreground">
          Upload Ericsson ENM PM counter files for analysis
        </p>
      </div>

      <div className="border-2 border-dashed rounded-lg p-12 text-center space-y-4">
        <UploadIcon className="h-12 w-12 mx-auto text-muted-foreground" />
        
        <div>
          <label
            htmlFor="file-upload"
            className="cursor-pointer inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            <File className="h-4 w-4 mr-2" />
            Select File
          </label>
          <input
            id="file-upload"
            type="file"
            accept=".xml.gz,.gz,.zip,.xml"
            onChange={handleFileChange}
            className="hidden"
            disabled={uploading || analyzing}
          />
        </div>

        {file && (
          <div className="mt-4 p-4 bg-muted rounded-md">
            <p className="text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-destructive/10 text-destructive rounded-md text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="mt-4 p-4 bg-green-500/10 text-green-600 dark:text-green-400 rounded-md text-sm">
            File uploaded successfully
          </div>
        )}

        <div className="flex gap-4 justify-center mt-6">
          <button
            onClick={handleUpload}
            disabled={!file || uploading || analyzing}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 inline animate-spin" />
                Uploading...
              </>
            ) : (
              'Upload & Analyze'
            )}
          </button>
        </div>

        {analyzing && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Analyzing PM data...
          </div>
        )}
      </div>

      <div className="bg-muted/50 p-4 rounded-lg text-sm space-y-2">
        <p className="font-semibold">File Requirements:</p>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
          <li>Format: Ericsson ENM PM XML (.xml.gz, .gz, .zip, or .xml)</li>
          <li>Contains PM counter measurements</li>
          <li>Includes timestamp, site, and KPI data</li>
          <li>ZIP files should contain XML files inside</li>
        </ul>
      </div>
    </div>
  )
}

