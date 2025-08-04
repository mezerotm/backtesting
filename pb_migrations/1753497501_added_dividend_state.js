/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const collection = db.getCollection("ry9f4uirrmnicou");
  
  // Add state field to dividends collection
  collection.schema.addField({
    "system": false,
    "id": "dividend_state",
    "name": "state",
    "type": "text",
    "required": false,
    "presentable": false,
    "unique": false,
    "options": {
      "min": null,
      "max": null,
      "pattern": ""
    }
  });

  return db.saveCollection(collection);
}, (db) => {
  const collection = db.getCollection("ry9f4uirrmnicou");
  
  // Remove state field from dividends collection
  collection.schema.removeField("dividend_state");
  
  return db.saveCollection(collection);
}) 