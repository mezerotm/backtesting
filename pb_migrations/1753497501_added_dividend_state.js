/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("ry9f4uirrmnicou");
  
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

  return dao.saveCollection(collection);
}, (db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("ry9f4uirrmnicou");
  
  // Remove state field from dividends collection
  collection.schema.removeField("dividend_state");
  
  return dao.saveCollection(collection);
}) 