// PreviewProvider.swift - the Space bar preview of an APlot graph.
//
// Pressing the Space bar on an .aplt file in the Finder (or choosing Quick
// Look from its menu) shows every diagram of the file: APlot stores them
// as a PDF, one page each (Thumbnails/preview.pdf), and Quick Look shows
// it the way it shows any PDF - scrolled through page by page, zoomed as
// far as wanted, and sharp at any size, since the pages are drawings.
//
// A graph saved by an older APlot has no PDF yet; it shows its single
// picture (Thumbnails/thumbnail.png) instead.  Either way this is a "data
// based" preview (macOS 12 and later): the extension hands Quick Look the
// data, and Quick Look draws it by itself.
//
// The window is asked to be `previewPoints` large along the longer side of
// the first page - far larger than any icon.

import Foundation
import CoreGraphics
import QuickLookUI
import UniformTypeIdentifiers

@objc(APlotPreviewProvider)
final class PreviewProvider: QLPreviewProvider, QLPreviewingController {

    /// How large the preview window is asked to be, in points.
    static let previewPoints: CGFloat = 1024

    func providePreview(for request: QLFilePreviewRequest) async throws -> QLPreviewReply {
        let box = CGSize(width: Self.previewPoints, height: Self.previewPoints)
        // every diagram of the file, when the file carries them
        if let pdf = try? APlotArchive.previewData(at: request.fileURL),
           let page = try? APlotArchive.firstPageSize(of: pdf) {
            let size = APlotArchive.fitting(page, into: box)
            return QLPreviewReply(dataOfContentType: .pdf, contentSize: size) { _ in pdf }
        }
        // ...or the one picture of an older graph
        let png = try APlotArchive.thumbnailData(at: request.fileURL)
        let image = try APlotArchive.image(from: png)
        let size = APlotArchive.fitting(CGSize(width: image.width, height: image.height),
                                        into: box)
        return QLPreviewReply(dataOfContentType: .png, contentSize: size) { _ in png }
    }
}
