package com.example.integrationServer;

import org.dom4j.Document;
import org.dom4j.io.DocumentResult;
import org.dom4j.io.DocumentSource;
import org.dom4j.io.OutputFormat;
import org.dom4j.io.SAXReader;
import org.dom4j.io.XMLWriter;
import org.dom4j.util.XMLErrorHandler;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.stream.StreamSource;
import java.io.File;
import java.io.StringReader;
import java.io.StringWriter;

@Service
public class XmlService {

    public String transform(String xml, String xslPath) throws Exception {
        SAXReader reader = new SAXReader();
        Document doc = reader.read(new StringReader(xml));

        ClassPathResource xsl = new ClassPathResource(xslPath);
        Transformer transformer = TransformerFactory.newInstance()
                .newTransformer(new StreamSource(xsl.getInputStream()));

        DocumentResult result = new DocumentResult();
        transformer.transform(new DocumentSource(doc), result);

        OutputFormat fmt = OutputFormat.createPrettyPrint();
        fmt.setEncoding("UTF-8");
        StringWriter sw = new StringWriter();
        XMLWriter writer = new XMLWriter(sw, fmt);
        writer.write(result.getDocument());
        writer.close();
        return sw.toString();
    }

    public void validate(String xml, String xsdPath) throws Exception {
        SAXReader saxReader = new SAXReader();
        saxReader.setValidation(true);
        saxReader.setFeature("http://xml.org/sax/features/validation", true);
        saxReader.setFeature("http://apache.org/xml/features/validation/schema", true);

        File xsdFile = new ClassPathResource(xsdPath).getFile();
        saxReader.setProperty(
                "http://apache.org/xml/properties/schema/external-noNamespaceSchemaLocation",
                xsdFile.toURI().toString());

        XMLErrorHandler errorHandler = new XMLErrorHandler();
        saxReader.setErrorHandler(errorHandler);
        saxReader.read(new StringReader(xml));

        if (errorHandler.getErrors().hasContent()) {
            throw new Exception("XSD validation failed: " + errorHandler.getErrors().asXML());
        }
    }

    public String buildResponse(String code, String message, String dataXml) {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Response>\n    <Code>" + code +
                "</Code>\n    <Message>" + message + "</Message>\n    <Data>" +
                (dataXml != null ? dataXml : "") + "</Data>\n</Response>";
    }
}
