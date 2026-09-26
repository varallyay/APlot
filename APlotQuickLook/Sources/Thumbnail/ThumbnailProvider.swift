// ThumbnailProvider.swift - the icon of an APlot graph in the Finder.
//
// Finder, the Open and Save dialogs and Spotlight ask this extension for
// the icon of every .aplt file they show.  The answer is the picture APlot
// stored in the file when it was saved - the first diagram of the file -
// scaled to the size that is asked for.  A graph without a picture (saved
// by an older APlot) gets an error back, and Finder shows the ordinary
// document icon for it instead.

import Foundation
import CoreGraphics
import QuickLookThumbnailing

@objc(APlotThumbnailProvider)
final class ThumbnailProvider: QLThumbnailProvider {

    override func provideThumbnail(for request: QLFileThumbnailRequest,
                                   _ handler: @escaping (QLThumbnailReply?, Error?) -> Void) {
        let image: CGImage
        do {
            image = try APlotArchive.thumbnailImage(at: request.fileURL)
        } catch {
            handler(nil, error)
            return
        }
        let size = APlotArchive.fitting(CGSize(width: image.width, height: image.height),
                                        into: request.maximumSize)
        // the size is in points: the context is made `request.scale` times
        // larger by Quick Look itself, so a Retina icon stays sharp
        let reply = QLThumbnailReply(contextSize: size, drawing: { (context: CGContext) -> Bool in
            context.interpolationQuality = .high
            context.draw(image, in: CGRect(origin: .zero, size: size))
            return true
        })
        handler(reply, nil)
    }
}
