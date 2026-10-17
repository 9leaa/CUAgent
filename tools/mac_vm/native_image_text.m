// Offline OCR of an existing image. No desktop APIs, input events or network.
#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>
#import <CommonCrypto/CommonDigest.h>

int main(int argc, const char **argv) {
    @autoreleasepool {
        if (argc != 2) return 2;
        NSData *data = [NSData dataWithContentsOfFile:@(argv[1])];
        if (!data || data.length == 0 || data.length > 20 * 1024 * 1024) return 3;
        CGImageSourceRef source = CGImageSourceCreateWithData((__bridge CFDataRef)data, NULL);
        if (!source) return 4;
        CGImageRef image = CGImageSourceCreateImageAtIndex(source, 0, NULL);
        CFRelease(source);
        if (!image) return 4;
        size_t width = CGImageGetWidth(image), height = CGImageGetHeight(image);
        if (width == 0 || height == 0 || width > 16384 || height > 16384) {
            CGImageRelease(image); return 4;
        }
        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        request.usesLanguageCorrection = NO;
        request.recognitionLanguages = @[@"en-US", @"zh-Hans"];
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc]
            initWithCGImage:image options:@{}];
        NSError *error = nil;
        BOOL ok = [handler performRequests:@[request] error:&error];
        CGImageRelease(image);
        if (!ok || error) return 5;
        NSMutableArray *items = [NSMutableArray array];
        for (VNRecognizedTextObservation *observation in request.results) {
            VNRecognizedText *text = [observation topCandidates:1].firstObject;
            if (!text) continue;
            CGRect b = observation.boundingBox;
            [items addObject:@{@"text": text.string, @"confidence": @(text.confidence),
                @"rect": @[@(b.origin.x * width), @((1 - CGRectGetMaxY(b)) * height),
                            @(b.size.width * width), @(b.size.height * height)]}];
        }
        unsigned char digest[CC_SHA256_DIGEST_LENGTH];
        CC_SHA256(data.bytes, (CC_LONG)data.length, digest);
        NSMutableString *sha = [NSMutableString string];
        for (unsigned i = 0; i < sizeof(digest); i++) [sha appendFormat:@"%02x", digest[i]];
        NSDictionary *report = @{@"version": @1, @"engine": @"AppleVision",
            @"sha256": sha, @"width": @(width), @"height": @(height), @"items": items};
        NSData *json = [NSJSONSerialization dataWithJSONObject:report options:0 error:&error];
        if (!json || error) return 6;
        [[NSFileHandle fileHandleWithStandardOutput] writeData:json];
        return 0;
    }
}
